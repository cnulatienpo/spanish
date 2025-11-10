using System.Text;
using Newtonsoft.Json.Linq;

namespace CodexFixer;

public record ConflictHealResult(string Text, int Blocks, List<Reject> Rejects);

public static class Conflicts
{
    public static ConflictHealResult ExtractAndHeal(string content, string path, DateTime modified)
    {
        var reader = new StringReader(content);
        var builder = new StringBuilder();
        var rejects = new List<Reject>();
        var blocks = 0;

        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            if (line.StartsWith("<<<<<<<"))
            {
                blocks++;
                var left = new List<string>();
                var right = new List<string>();
                string? marker;
                while ((marker = reader.ReadLine()) != null && !marker.StartsWith("======="))
                {
                    left.Add(marker);
                }

                if (marker is null)
                {
                    rejects.Add(new Reject(path, "unterminated conflict", string.Join('\n', left)));
                    break;
                }

                while ((marker = reader.ReadLine()) != null && !marker.StartsWith(">>>>>>>"))
                {
                    right.Add(marker);
                }

                if (marker is null)
                {
                    rejects.Add(new Reject(path, "unterminated conflict", string.Join('\n', right)));
                    break;
                }

                var resolved = ResolveBlock(left, right, path, modified, rejects);
                if (!string.IsNullOrEmpty(resolved))
                {
                    builder.AppendLine(resolved);
                }
            }
            else
            {
                builder.AppendLine(line);
            }
        }

        return new ConflictHealResult(builder.ToString(), blocks, rejects);
    }

    private static string ResolveBlock(List<string> left, List<string> right, string path, DateTime modified, List<Reject> rejects)
    {
        var leftText = string.Join('\n', left);
        var rightText = string.Join('\n', right);

        if (Normalize.TryParseLoose(leftText, out var leftToken) && Normalize.TryParseLoose(rightText, out var rightToken))
        {
            var merged = Merge.DeepMerge(leftToken!, rightToken!, modified, modified, path);
            return merged.ToString(Newtonsoft.Json.Formatting.Indented);
        }

        if (Normalize.TryParseLoose(leftText, out leftToken))
        {
            return leftToken!.ToString(Newtonsoft.Json.Formatting.Indented);
        }

        if (Normalize.TryParseLoose(rightText, out rightToken))
        {
            return rightToken!.ToString(Newtonsoft.Json.Formatting.Indented);
        }

        var prefer = SelectByHeuristic(leftText, rightText, modified, modified);
        if (!string.IsNullOrEmpty(prefer.Selected))
        {
            rejects.Add(new Reject(path, "conflict-unparsed", prefer.Rejected));
            return prefer.Selected;
        }

        rejects.Add(new Reject(path, "conflict-unresolved", leftText + "\n=======\n" + rightText));
        return string.Empty;
    }

    private static (string Selected, string Rejected) SelectByHeuristic(string left, string right, DateTime leftTime, DateTime rightTime)
    {
        if (rightTime > leftTime)
        {
            return (right, left);
        }

        if (leftTime > rightTime)
        {
            return (left, right);
        }

        return left.Length >= right.Length ? (left, right) : (right, left);
    }
}
