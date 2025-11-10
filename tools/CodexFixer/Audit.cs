using System.Text;
using System.Linq;
using Humanizer;
using Murmur;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Spectre.Console;

namespace CodexFixer;

public record AuditMetrics(
    int FilesScanned,
    int ConflictBlocks,
    int ParsedItems,
    int DuplicateClusters,
    int VocabularyCount,
    int LessonCount,
    IReadOnlyList<string> UnsetLevelIds,
    IReadOnlyList<Reject> Rejects,
    TimeSpan Duration);

public static class Audit
{
    public static string BuildMarkdown(AuditMetrics metrics)
    {
        var sb = new StringBuilder();
        sb.AppendLine("# CodexFixer Audit");
        sb.AppendLine();
        sb.AppendLine($"* Files scanned: {metrics.FilesScanned}");
        sb.AppendLine($"* Conflict blocks repaired: {metrics.ConflictBlocks}");
        sb.AppendLine($"* Items parsed: {metrics.ParsedItems}");
        sb.AppendLine($"* Vocabulary canonicalized: {metrics.VocabularyCount}");
        sb.AppendLine($"* Lessons canonicalized: {metrics.LessonCount}");
        sb.AppendLine($"* Duplicate clusters merged: {metrics.DuplicateClusters}");
        sb.AppendLine($"* Duration: {metrics.Duration.Humanize(precision: 2)}");
        sb.AppendLine();

        if (metrics.UnsetLevelIds.Count > 0)
        {
            sb.AppendLine("## Items with UNSET level");
            foreach (var id in metrics.UnsetLevelIds)
            {
                sb.AppendLine($"- {id}");
            }

            sb.AppendLine();
        }

        if (metrics.Rejects.Count > 0)
        {
            sb.AppendLine("## Rejects");
            foreach (var reject in metrics.Rejects)
            {
                sb.AppendLine($"- **{reject.SourceFile}** – {reject.Reason}");
            }

            sb.AppendLine();
        }

        return sb.ToString();
    }

    public static void PrintToConsole(AuditMetrics metrics)
    {
        AnsiConsole.WriteLine($"🔍 Scanned {metrics.FilesScanned:N0} files");
        AnsiConsole.WriteLine($"⚔️  Repaired {metrics.ConflictBlocks:N0} conflict blocks");
        AnsiConsole.WriteLine($"📚  {metrics.VocabularyCount:N0} vocab | {metrics.LessonCount:N0} lessons");
        AnsiConsole.WriteLine($"✅  {metrics.DuplicateClusters:N0} duplicate clusters merged");
        var unset = metrics.UnsetLevelIds.Count;
        var prefix = unset > 0 ? "⚠️" : "✅";
        AnsiConsole.WriteLine($"{prefix}  {unset:N0} items with UNSET level");
        AnsiConsole.WriteLine($"🚫  {metrics.Rejects.Count:N0} rejects saved");
        AnsiConsole.WriteLine("✨ Done — canonical JSONs in build/canonical/");
    }

    public static void VerifyIdempotent(JArray lessons, JArray vocabulary)
    {
        var firstLessons = ComputeHash(lessons);
        var secondLessons = ComputeHash(JArray.Parse(lessons.ToString(Formatting.None)));
        if (!firstLessons.SequenceEqual(secondLessons))
        {
            throw new InvalidOperationException("Lessons output failed idempotency check");
        }

        var firstVocab = ComputeHash(vocabulary);
        var secondVocab = ComputeHash(JArray.Parse(vocabulary.ToString(Formatting.None)));
        if (!firstVocab.SequenceEqual(secondVocab))
        {
            throw new InvalidOperationException("Vocabulary output failed idempotency check");
        }
    }

    private static byte[] ComputeHash(JArray array)
    {
        var bytes = Encoding.UTF8.GetBytes(array.ToString(Formatting.None));
        using var hash = MurmurHash.Create128();
        return hash.ComputeHash(bytes);
    }
}
