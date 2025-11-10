using System.Text;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace CodexFixer;

public static class Merge
{
    public static JToken DeepMerge(JToken left, JToken right, DateTime? leftTime, DateTime? rightTime, string sourcePath, string path = "")
    {
        if (left is JObject leftObj && right is JObject rightObj)
        {
            var result = new JObject();
            var propertyNames = new HashSet<string>(leftObj.Properties().Select(p => p.Name), StringComparer.Ordinal);
            propertyNames.UnionWith(rightObj.Properties().Select(p => p.Name));
            string? notesAlt = null;
            var existingAltLeft = leftObj.Value<string>("notes_alt_variant");
            var existingAltRight = rightObj.Value<string>("notes_alt_variant");

            foreach (var name in propertyNames)
            {
                var nextPath = string.IsNullOrEmpty(path) ? name : path + "." + name;
                var leftValue = leftObj[name];
                var rightValue = rightObj[name];

                if (name == "notes" && leftValue is not null && rightValue is not null)
                {
                    var (noteValue, alt) = ResolveNotes(leftValue, rightValue, leftTime, rightTime);
                    if (noteValue is not null)
                    {
                        result[name] = noteValue;
                    }

                    if (!string.IsNullOrWhiteSpace(alt))
                    {
                        notesAlt = alt;
                    }

                    continue;
                }

                if (leftValue is null)
                {
                    result[name] = rightValue?.DeepClone();
                }
                else if (rightValue is null)
                {
                    result[name] = leftValue.DeepClone();
                }
                else if (name == "source_files" && leftValue is JArray leftArray && rightValue is JArray rightArray)
                {
                    result[name] = MergeArrays(leftArray, rightArray);
                }
                else
                {
                    result[name] = DeepMerge(leftValue, rightValue, leftTime, rightTime, sourcePath, nextPath);
                }
            }

            var allAlts = new List<string>();
            if (!string.IsNullOrWhiteSpace(existingAltLeft))
            {
                allAlts.Add(existingAltLeft!);
            }

            if (!string.IsNullOrWhiteSpace(existingAltRight))
            {
                allAlts.Add(existingAltRight!);
            }

            if (!string.IsNullOrWhiteSpace(notesAlt))
            {
                allAlts.Add(notesAlt!);
            }

            if (allAlts.Count > 0)
            {
                result["notes_alt_variant"] = string.Join("\n\n— MERGED VARIANT —\n\n", allAlts.Distinct(StringComparer.Ordinal));
            }

            return result;
        }

        if (left is JArray leftArr && right is JArray rightArr)
        {
            return MergeArrays(leftArr, rightArr);
        }

        if (left.Type == JTokenType.String && right.Type == JTokenType.String)
        {
            var leftValue = left.ToString();
            var rightValue = right.ToString();
            if (string.Equals(leftValue, rightValue, StringComparison.Ordinal))
            {
                return new JValue(leftValue);
            }

            if (IsConcatenatedField(path))
            {
                var merged = ConcatenateVariants(leftValue, rightValue);
                return new JValue(merged);
            }

            var chosen = SelectScalar(leftValue, rightValue, leftTime, rightTime, out var rejected);
            if (!string.IsNullOrEmpty(rejected) && path.EndsWith("notes", StringComparison.Ordinal))
            {
                return new JObject
                {
                    ["notes"] = new JValue(chosen),
                    ["notes_alt_variant"] = new JValue(rejected)
                };
            }

            return new JValue(chosen);
        }

        if (left.Type != right.Type)
        {
            // prefer non-null type
            if (right.Type == JTokenType.Null)
            {
                return left.DeepClone();
            }

            if (left.Type == JTokenType.Null)
            {
                return right.DeepClone();
            }

            var preferRight = ShouldPreferRight(leftTime, rightTime, left, right);
            return preferRight ? right.DeepClone() : left.DeepClone();
        }

        if (ShouldPreferRight(leftTime, rightTime, left, right))
        {
            return right.DeepClone();
        }

        return left.DeepClone();
    }

    private static (JToken? Value, string? Alt) ResolveNotes(JToken left, JToken right, DateTime? leftTime, DateTime? rightTime)
    {
        var leftValue = left.Type == JTokenType.String ? left.ToString() : left.ToString(Newtonsoft.Json.Formatting.None);
        var rightValue = right.Type == JTokenType.String ? right.ToString() : right.ToString(Newtonsoft.Json.Formatting.None);
        if (string.Equals(leftValue, rightValue, StringComparison.Ordinal))
        {
            return (new JValue(leftValue), null);
        }

        var chosen = SelectScalar(leftValue, rightValue, leftTime, rightTime, out var rejected);
        return (new JValue(chosen), rejected);
    }

    private static bool ShouldPreferRight(DateTime? leftTime, DateTime? rightTime, JToken left, JToken right)
    {
        if (rightTime.HasValue && leftTime.HasValue)
        {
            if (rightTime.Value > leftTime.Value)
            {
                return true;
            }

            if (leftTime.Value > rightTime.Value)
            {
                return false;
            }
        }

        var leftLength = left.Type == JTokenType.String ? left.ToString().Length : left.ToString(Formatting.None).Length;
        var rightLength = right.Type == JTokenType.String ? right.ToString().Length : right.ToString(Formatting.None).Length;
        if (rightLength != leftLength)
        {
            return rightLength > leftLength;
        }

        return false;
    }

    private static string SelectScalar(string left, string right, DateTime? leftTime, DateTime? rightTime, out string rejected)
    {
        var preferRight = ShouldPreferRight(leftTime, rightTime, new JValue(left), new JValue(right));
        if (preferRight)
        {
            rejected = left;
            return right;
        }

        rejected = right;
        return left;
    }

    private static bool IsConcatenatedField(string path)
    {
        if (string.IsNullOrEmpty(path))
        {
            return false;
        }

        return path.EndsWith("definition", StringComparison.Ordinal) ||
               path.EndsWith("origin", StringComparison.Ordinal) ||
               path.EndsWith("story", StringComparison.Ordinal);
    }

    private static string ConcatenateVariants(string a, string b)
    {
        if (string.Equals(a, b, StringComparison.Ordinal))
        {
            return a;
        }

        if (string.IsNullOrWhiteSpace(a))
        {
            return b;
        }

        if (string.IsNullOrWhiteSpace(b))
        {
            return a;
        }

        return a.TrimEnd() + "\n\n— MERGED VARIANT —\n\n" + b.TrimStart();
    }

    private static JArray MergeArrays(JArray left, JArray right)
    {
        var results = new List<JToken>();
        var seen = new HashSet<string>(StringComparer.Ordinal);

        void AddRange(JArray array)
        {
            foreach (var item in array)
            {
                var key = BuildArrayKey(item);
                if (seen.Add(key))
                {
                    results.Add(item.DeepClone());
                }
            }
        }

        AddRange(left);
        AddRange(right);

        return new JArray(results);
    }

    private static string BuildArrayKey(JToken token)
    {
        if (token.Type == JTokenType.String)
        {
            return NormalizeWhitespace(token.ToString());
        }

        return token.ToString(Newtonsoft.Json.Formatting.None);
    }

    private static string NormalizeWhitespace(string text)
    {
        var builder = new StringBuilder(text.Length);
        var previousSpace = false;
        foreach (var ch in text)
        {
            if (char.IsWhiteSpace(ch))
            {
                if (!previousSpace)
                {
                    builder.Append(' ');
                    previousSpace = true;
                }
            }
            else
            {
                builder.Append(ch);
                previousSpace = false;
            }
        }

        return builder.ToString().Trim();
    }
}
