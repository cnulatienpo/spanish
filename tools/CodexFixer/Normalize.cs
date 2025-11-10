using System.Text;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Slugify;

namespace CodexFixer;

public record NormalizationOutcome(List<CandidateResult> Candidates, List<Reject> Rejects, int ParsedItems);

public static class Normalize
{
    private static readonly Regex BareKeyRegex = new("(?<=^|[,{\n\r])\\s*([A-Za-z0-9_]+)\\s*:(?!\\s*\\\")", RegexOptions.Compiled);
    private static readonly Regex SingleQuoteKeyRegex = new("'(?<key>[^']+)'\\s*:", RegexOptions.Compiled);
    private static readonly Regex SingleQuoteValueRegex = new(":\\s*'(?<value>(?:\\\'|[^'])*)'", RegexOptions.Compiled);
    private static readonly Regex TrailingCommaRegex = new(",\\s*(?=[}\]])", RegexOptions.Compiled);
    private static readonly Regex LevelRegex = new("(?i)\\b(A1|A2|B1|B2|C1|C2)\\b", RegexOptions.Compiled);
    private static readonly SlugHelper Slugger = new();

    public static NormalizationOutcome ExtractCandidates(string text, string sourcePath, DateTime modified)
    {
        var rejects = new List<Reject>();
        var tokens = ExtractTokens(text);
        var candidates = new List<CandidateResult>();
        var parsedCount = 0;

        var queue = new Queue<JToken>(tokens);
        while (queue.Count > 0)
        {
            var token = queue.Dequeue();
            if (token is JObject obj)
            {
                parsedCount++;
                NormalizeLevel(obj, sourcePath);
                EnsureSourceFiles(obj, sourcePath);

                var isLesson = LooksLikeLesson(obj);
                var isVocab = LooksLikeVocabulary(obj);

                if (isLesson)
                {
                    var lessonObj = NormalizeLesson(obj.DeepClone() as JObject ?? new JObject(), sourcePath);
                    if (lessonObj is not null)
                    {
                        candidates.Add(new CandidateResult("lesson", lessonObj, modified, ExtractSourceSet(lessonObj), ModelHelpers.LessonKey(lessonObj)));
                    }
                    else
                    {
                        rejects.Add(new Reject(sourcePath, "invalid-lesson", obj.ToString(Formatting.None)));
                    }
                }

                if (isVocab)
                {
                    var vocabObj = NormalizeVocabulary(obj.DeepClone() as JObject ?? new JObject(), sourcePath);
                    if (vocabObj is not null)
                    {
                        candidates.Add(new CandidateResult("vocab", vocabObj, modified, ExtractSourceSet(vocabObj), ModelHelpers.VocabularyKey(vocabObj)));
                    }
                    else
                    {
                        rejects.Add(new Reject(sourcePath, "invalid-vocabulary", obj.ToString(Formatting.None)));
                    }
                }

                if (!isLesson && !isVocab)
                {
                    rejects.Add(new Reject(sourcePath, "unclassified", obj.ToString(Formatting.None)));
                }
            }
            else if (token is JArray arr)
            {
                foreach (var child in arr)
                {
                    queue.Enqueue(child);
                }
            }
        }

        return new NormalizationOutcome(candidates, rejects, parsedCount);
    }

    public static bool TryParseLoose(string text, out JToken? token)
    {
        var repaired = RepairText(text);
        if (string.IsNullOrWhiteSpace(repaired))
        {
            token = null;
            return false;
        }

        try
        {
            token = JToken.Parse(repaired);
            return true;
        }
        catch
        {
            token = null;
            return false;
        }
    }

    private static List<JToken> ExtractTokens(string text)
    {
        var tokens = new List<JToken>();
        if (TryParseLoose(text, out var token) && token is not null)
        {
            if (token.Type == JTokenType.Array)
            {
                foreach (var item in token.Children())
                {
                    tokens.Add(item);
                }
            }
            else
            {
                tokens.Add(token);
            }

            return tokens;
        }

        var repaired = RepairText(text);
        var reader = new JsonTextReader(new StringReader(repaired))
        {
            SupportMultipleContent = true
        };

        try
        {
            while (reader.Read())
            {
                var segment = JToken.ReadFrom(reader);
                tokens.Add(segment);
            }
        }
        catch
        {
            // Fallback: treat as raw text failure.
        }

        return tokens;
    }

    private static JObject? NormalizeLesson(JObject obj, string sourcePath)
    {
        var title = obj.Value<string>("title")?.Trim();
        if (string.IsNullOrWhiteSpace(title))
        {
            return null;
        }

        obj["title"] = title;
        obj["level"] = Cefr.Normalize(obj.Value<string>("level"));
        obj["unit"] = ParseInt(obj["unit"]);
        obj["lesson_number"] = ParseInt(obj["lesson_number"]);

        var nickname = obj.Value<string>("nickname");
        if (string.IsNullOrWhiteSpace(nickname))
        {
            obj["nickname"] = Slugger.GenerateSlug(title);
        }

        obj["tags"] = NormalizeStringArray(obj["tags"]);
        obj["steps"] = NormalizeSteps(obj["steps"]);
        obj["source_files"] = NormalizeStringArray(obj["source_files"], sourcePath);

        if (obj["id"] is null || string.IsNullOrWhiteSpace(obj.Value<string>("id")))
        {
            obj["id"] = Lesson.BuildId(obj.Value<int?>("unit") ?? 0, title);
        }

        return obj;
    }

    private static JObject? NormalizeVocabulary(JObject obj, string sourcePath)
    {
        var spanish = obj.Value<string>("spanish")?.Trim();
        if (string.IsNullOrWhiteSpace(spanish))
        {
            return null;
        }

        obj["spanish"] = spanish;
        var pos = obj.Value<string>("pos") ?? obj.Value<string>("part_of_speech") ?? "expr";
        obj["pos"] = pos;
        obj["level"] = Cefr.Normalize(obj.Value<string>("level"));
        obj["tags"] = NormalizeStringArray(obj["tags"]);
        obj["examples"] = NormalizeExamples(obj["examples"]);
        obj["source_files"] = NormalizeStringArray(obj["source_files"], sourcePath);

        if (obj["definition"] is null)
        {
            obj["definition"] = "";
        }

        if (obj["english_gloss"] is null)
        {
            obj["english_gloss"] = "";
        }

        if (obj["id"] is null || string.IsNullOrWhiteSpace(obj.Value<string>("id")))
        {
            var gender = obj.Value<string>("gender") ?? "null";
            obj["id"] = Vocabulary.BuildId(spanish, obj.Value<string>("pos") ?? "expr", gender);
        }

        return obj;
    }

    private static void NormalizeLevel(JObject obj, string sourcePath)
    {
        var level = obj.Value<string>("level");
        if (!string.IsNullOrWhiteSpace(level))
        {
            obj["level"] = Cefr.Normalize(level);
            return;
        }

        var inferred = InferLevelFromPath(sourcePath) ?? InferLevelFromTags(obj);
        obj["level"] = Cefr.Normalize(inferred);
    }

    private static string? InferLevelFromPath(string path)
    {
        foreach (Match match in LevelRegex.Matches(path))
        {
            return match.Value.ToUpperInvariant();
        }

        return null;
    }

    private static string? InferLevelFromTags(JObject obj)
    {
        if (obj["tags"] is JArray arr)
        {
            foreach (var token in arr.Values<string>())
            {
                var match = LevelRegex.Match(token ?? string.Empty);
                if (match.Success)
                {
                    return match.Value.ToUpperInvariant();
                }
            }
        }

        return null;
    }

    private static void EnsureSourceFiles(JObject obj, string sourcePath)
    {
        var array = NormalizeStringArray(obj["source_files"], sourcePath);
        obj["source_files"] = array;
    }

    private static JArray NormalizeStringArray(JToken? token, string? appendValue = null)
    {
        var values = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        void AddValue(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return;
            }

            var trimmed = value.Trim();
            if (seen.Add(trimmed))
            {
                values.Add(trimmed);
            }
        }

        if (token is JArray arr)
        {
            foreach (var item in arr.Values<string>())
            {
                AddValue(item);
            }
        }

        AddValue(appendValue);

        return new JArray(values);
    }

    private static JArray NormalizeSteps(JToken? token)
    {
        var steps = new List<JObject>();
        if (token is JArray arr)
        {
            foreach (var entry in arr)
            {
                if (entry is JObject obj)
                {
                    var phase = obj.Value<string>("phase") ?? "examples";
                    if (!Enum.TryParse<LessonPhase>(phase, true, out var parsed))
                    {
                        parsed = LessonPhase.examples;
                    }

                    var normalized = new JObject
                    {
                        ["phase"] = parsed.ToString()
                    };

                    if (obj["line"] != null)
                    {
                        normalized["line"] = obj["line"];
                    }

                    if (obj["origin"] != null)
                    {
                        normalized["origin"] = obj["origin"];
                    }

                    if (obj["story"] != null)
                    {
                        normalized["story"] = obj["story"];
                    }

                    if (obj["items"] is JArray items)
                    {
                        normalized["items"] = NormalizeStringArray(items);
                    }

                    steps.Add(normalized);
                }
                else if (entry.Type == JTokenType.String)
                {
                    steps.Add(new JObject
                    {
                        ["phase"] = LessonPhase.examples.ToString(),
                        ["line"] = entry
                    });
                }
            }
        }

        return new JArray(steps);
    }

    private static JArray NormalizeExamples(JToken? token)
    {
        var list = new List<JObject>();
        if (token is JArray arr)
        {
            foreach (var entry in arr)
            {
                if (entry is JObject obj)
                {
                    var es = obj.Value<string>("es") ?? obj.Value<string>("spanish");
                    var en = obj.Value<string>("en") ?? obj.Value<string>("english");
                    if (!string.IsNullOrWhiteSpace(es) || !string.IsNullOrWhiteSpace(en))
                    {
                        list.Add(new JObject
                        {
                            ["es"] = es ?? string.Empty,
                            ["en"] = en ?? string.Empty
                        });
                    }
                }
                else if (entry.Type == JTokenType.String)
                {
                    var text = entry.ToString();
                    list.Add(new JObject
                    {
                        ["es"] = text,
                        ["en"] = text
                    });
                }
            }
        }

        return new JArray(list);
    }

    private static int ParseInt(JToken? token)
    {
        if (token is null)
        {
            return 0;
        }

        if (token.Type == JTokenType.Integer)
        {
            return token.Value<int>();
        }

        if (token.Type == JTokenType.String && int.TryParse(token.ToString(), out var value))
        {
            return value;
        }

        return 0;
    }

    private static bool LooksLikeLesson(JObject obj)
    {
        return obj["title"] != null && obj["steps"] != null;
    }

    private static bool LooksLikeVocabulary(JObject obj)
    {
        return obj["spanish"] != null && (obj["definition"] != null || obj["english_gloss"] != null);
    }

    private static HashSet<string> ExtractSourceSet(JObject obj)
    {
        var result = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (obj["source_files"] is JArray arr)
        {
            foreach (var file in arr.Values<string>())
            {
                if (!string.IsNullOrWhiteSpace(file))
                {
                    result.Add(file.Trim());
                }
            }
        }

        return result;
    }

    private static string RepairText(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
        {
            return string.Empty;
        }

        var repaired = text;
        repaired = SingleQuoteKeyRegex.Replace(repaired, m => $"\"{m.Groups["key"].Value}\":");
        repaired = BareKeyRegex.Replace(repaired, m => m.Value.Replace(m.Groups[1].Value, $"\"{m.Groups[1].Value}\""));
        repaired = SingleQuoteValueRegex.Replace(repaired, m => $": \"{m.Groups["value"].Value.Replace("\"", "\\\"")}\"");
        repaired = TrailingCommaRegex.Replace(repaired, string.Empty);
        repaired = BalanceBrackets(repaired);
        return repaired;
    }

    private static string BalanceBrackets(string text)
    {
        var openCurly = text.Count(c => c == '{');
        var closeCurly = text.Count(c => c == '}');
        var openSquare = text.Count(c => c == '[');
        var closeSquare = text.Count(c => c == ']');

        var builder = new StringBuilder(text);
        builder.Append(new string('}', Math.Max(0, openCurly - closeCurly)));
        builder.Append(new string(']', Math.Max(0, openSquare - closeSquare)));
        return builder.ToString();
    }
}
