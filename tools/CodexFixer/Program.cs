using System.CommandLine;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using Json.Schema;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace CodexFixer;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        var root = new RootCommand("CodexFixer heals conflicted lesson and vocabulary data");
        var checkOption = new Option<bool>("--check", description: "Print audit without writing canonical files");
        var writeOption = new Option<bool>("--write", description: "Write canonical outputs (default)");
        var strictOption = new Option<bool>("--strict", description: "Fail if schema invalid or level=UNSET");

        root.SetHandler((bool check, bool write, bool strict) => RunAsync(check, write, strict), checkOption, writeOption, strictOption);

        return await root.InvokeAsync(args);
    }

    private static Task RunAsync(bool check, bool write, bool strict)
    {
        var shouldWrite = write || !check;
        var stopwatch = Stopwatch.StartNew();
        var files = IO.EnumerateContentFiles("content").ToList();
        var rejects = new List<Reject>();
        var conflictBlocks = 0;
        var parsedItems = 0;

        var lessonMap = new Dictionary<string, CandidateAccumulator>(StringComparer.OrdinalIgnoreCase);
        var vocabMap = new Dictionary<string, CandidateAccumulator>(StringComparer.OrdinalIgnoreCase);
        var duplicateClusters = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var file in files)
        {
            string content;
            try
            {
                content = IO.ReadAllText(file);
            }
            catch (Exception ex)
            {
                rejects.Add(new Reject(file, "read-error", ex.Message));
                continue;
            }

            var modified = IO.GetModifiedTime(file);
            var healed = Conflicts.ExtractAndHeal(content, file, modified);
            conflictBlocks += healed.Blocks;
            rejects.AddRange(healed.Rejects);

            var normalization = Normalize.ExtractCandidates(healed.Text, file, modified);
            parsedItems += normalization.ParsedItems;
            rejects.AddRange(normalization.Rejects);

            foreach (var candidate in normalization.Candidates)
            {
                if (candidate.Kind == "lesson")
                {
                    if (lessonMap.TryGetValue(candidate.Key, out var existing))
                    {
                        existing.Merge(candidate);
                        duplicateClusters.Add(candidate.Key);
                    }
                    else
                    {
                        lessonMap[candidate.Key] = new CandidateAccumulator(candidate);
                    }
                }
                else if (candidate.Kind == "vocab")
                {
                    if (vocabMap.TryGetValue(candidate.Key, out var existing))
                    {
                        existing.Merge(candidate);
                        duplicateClusters.Add(candidate.Key);
                    }
                    else
                    {
                        vocabMap[candidate.Key] = new CandidateAccumulator(candidate);
                    }
                }
            }
        }

        var lessons = lessonMap.Values.Select(acc => ModelHelpers.ToLesson(acc.ToCandidateResult())).ToList();
        var vocabulary = vocabMap.Values.Select(acc => ModelHelpers.ToVocabulary(acc.ToCandidateResult())).ToList();

        lessons = lessons
            .OrderBy(l => Cefr.Order(l.Level))
            .ThenBy(l => l.Unit == 0 ? 9999 : l.Unit)
            .ThenBy(l => l.LessonNumber == 0 ? 9999 : l.LessonNumber)
            .ThenBy(l => l.Id, StringComparer.Ordinal)
            .ToList();

        vocabulary = vocabulary
            .OrderBy(v => Cefr.Order(v.Level))
            .ThenBy(v => v.Spanish, StringComparer.OrdinalIgnoreCase)
            .ThenBy(v => v.Pos, StringComparer.OrdinalIgnoreCase)
            .ThenBy(v => v.Id, StringComparer.Ordinal)
            .ToList();

        var unsetIds = lessons.Where(l => l.Level == "UNSET").Select(l => l.Id)
            .Concat(vocabulary.Where(v => v.Level == "UNSET").Select(v => v.Id))
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToList();

        var serializer = JsonSerializer.Create(new JsonSerializerSettings
        {
            NullValueHandling = NullValueHandling.Ignore
        });

        var lessonSchema = JsonSchema.FromText(File.ReadAllText("tools/CodexFixer/Schemas/lesson.schema.json"));
        var vocabSchema = JsonSchema.FromText(File.ReadAllText("tools/CodexFixer/Schemas/vocab.schema.json"));
        var schemaRejects = new List<Reject>();

        foreach (var lesson in lessons)
        {
            var token = JObject.FromObject(lesson, serializer);
            var result = lessonSchema.Evaluate(token, new EvaluationOptions { OutputFormat = OutputFormat.List });
            if (!result.IsValid)
            {
                var reason = string.Join("; ", result.Details.Where(d => !d.IsValid).Select(d => d.Message));
                schemaRejects.Add(new Reject(string.Join(",", lesson.SourceFiles), $"lesson-schema:{lesson.Id}", reason));
            }
        }

        foreach (var vocab in vocabulary)
        {
            var token = JObject.FromObject(vocab, serializer);
            var result = vocabSchema.Evaluate(token, new EvaluationOptions { OutputFormat = OutputFormat.List });
            if (!result.IsValid)
            {
                var reason = string.Join("; ", result.Details.Where(d => !d.IsValid).Select(d => d.Message));
                schemaRejects.Add(new Reject(string.Join(",", vocab.SourceFiles), $"vocab-schema:{vocab.Id}", reason));
            }
        }

        rejects.AddRange(schemaRejects);

        if (strict)
        {
            if (unsetIds.Count > 0)
            {
                throw new InvalidOperationException("Strict mode: UNSET levels found");
            }

            if (schemaRejects.Count > 0)
            {
                throw new InvalidOperationException("Strict mode: schema validation failed");
            }
        }

        var vocabularyArray = IO.ToJArray(vocabulary);
        var lessonsArray = IO.ToJArray(lessons);
        Audit.VerifyIdempotent(lessonsArray, vocabularyArray);

        if (shouldWrite)
        {
            IO.WriteJsonArray(Path.Combine("build", "canonical", "lessons.mmspanish.json"), lessons);
            IO.WriteJsonArray(Path.Combine("build", "canonical", "vocabulary.mmspanish.json"), vocabulary);
            WriteRejects(rejects);
            var markdown = Audit.BuildMarkdown(new AuditMetrics(
                files.Count,
                conflictBlocks,
                parsedItems,
                duplicateClusters.Count,
                vocabulary.Count,
                lessons.Count,
                unsetIds,
                rejects,
                stopwatch.Elapsed));
            IO.WriteAudit(Path.Combine("build", "reports", "audit.md"), markdown);
        }

        Audit.PrintToConsole(new AuditMetrics(
            files.Count,
            conflictBlocks,
            parsedItems,
            duplicateClusters.Count,
            vocabulary.Count,
            lessons.Count,
            unsetIds,
            rejects,
            stopwatch.Elapsed));

        return Task.CompletedTask;
    }

    private static void WriteRejects(IReadOnlyList<Reject> rejects)
    {
        var baseDir = Path.Combine("build", "rejects");
        if (Directory.Exists(baseDir))
        {
            foreach (var file in Directory.EnumerateFiles(baseDir))
            {
                File.Delete(file);
            }
        }

        Directory.CreateDirectory(baseDir);
        var ordered = rejects
            .OrderBy(r => r.SourceFile, StringComparer.OrdinalIgnoreCase)
            .ThenBy(r => r.Reason, StringComparer.OrdinalIgnoreCase)
            .ThenBy(r => r.Snippet, StringComparer.Ordinal)
            .ToList();

        for (var index = 0; index < ordered.Count; index++)
        {
            var reject = ordered[index];
            var name = $"reject_{index + 1:0000}.txt";
            var path = Path.Combine(baseDir, name);
            var builder = new System.Text.StringBuilder();
            builder.AppendLine($"Source: {reject.SourceFile}");
            builder.AppendLine($"Reason: {reject.Reason}");
            builder.AppendLine();
            builder.AppendLine(reject.Snippet);
            File.WriteAllText(path, builder.ToString());
        }
    }

    private sealed class CandidateAccumulator
    {
        public CandidateAccumulator(CandidateResult initial)
        {
            Kind = initial.Kind;
            Key = initial.Key;
            Data = (JObject)initial.Data.DeepClone();
            Modified = initial.Modified;
            SourceFiles = new HashSet<string>(initial.SourceFiles, StringComparer.OrdinalIgnoreCase);
        }

        public string Kind { get; }
        public string Key { get; }
        public JObject Data { get; private set; }
        public DateTime Modified { get; private set; }
        public HashSet<string> SourceFiles { get; }

        public void Merge(CandidateResult next)
        {
            var merged = Merge.DeepMerge(Data, next.Data, Modified, next.Modified, Key);
            if (merged is JObject obj)
            {
                Data = obj;
            }
            else if (merged is JValue value && value.Value is JObject valueObj)
            {
                Data = valueObj;
            }
            else
            {
                Data = new JObject
                {
                    ["value"] = merged
                };
            }

            Modified = next.Modified > Modified ? next.Modified : Modified;
            SourceFiles.UnionWith(next.SourceFiles);
            Data["source_files"] = new JArray(SourceFiles.OrderBy(f => f, StringComparer.OrdinalIgnoreCase));
        }

        public CandidateResult ToCandidateResult()
        {
            Data["source_files"] = new JArray(SourceFiles.OrderBy(f => f, StringComparer.OrdinalIgnoreCase));
            return new CandidateResult(Kind, (JObject)Data.DeepClone(), Modified, new HashSet<string>(SourceFiles, StringComparer.OrdinalIgnoreCase), Key);
        }
    }
}
