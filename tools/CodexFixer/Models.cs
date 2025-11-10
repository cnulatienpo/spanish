using System.Text;
using Murmur;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Slugify;

namespace CodexFixer;

public static class Cefr
{
    private static readonly Dictionary<string, int> OrderMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["A1"] = 1,
        ["A2"] = 2,
        ["B1"] = 3,
        ["B2"] = 4,
        ["C1"] = 5,
        ["C2"] = 6,
        ["UNSET"] = 7
    };

    public static string Normalize(string? level)
    {
        if (string.IsNullOrWhiteSpace(level))
        {
            return "UNSET";
        }

        var upper = level.Trim().ToUpperInvariant();
        return OrderMap.ContainsKey(upper) ? upper : "UNSET";
    }

    public static int Order(string? level)
    {
        if (string.IsNullOrWhiteSpace(level))
        {
            return OrderMap["UNSET"];
        }

        return OrderMap.TryGetValue(level!, out var value) ? value : OrderMap["UNSET"];
    }
}

public enum LessonPhase
{
    english_anchor,
    system_logic,
    meaning_depth,
    spanish_entry,
    examples
}

public class LessonStep
{
    [JsonProperty("phase")]
    public LessonPhase Phase { get; set; }

    [JsonProperty("line")]
    public string? Line { get; set; }

    [JsonProperty("origin")]
    public string? Origin { get; set; }

    [JsonProperty("story")]
    public string? Story { get; set; }

    [JsonProperty("items")]
    public List<string>? Items { get; set; }

    public LessonStep()
    {
    }

    public LessonStep(JObject obj)
    {
        var phaseToken = obj["phase"]?.ToString();
        if (phaseToken is null)
        {
            throw new InvalidOperationException("Lesson step requires phase");
        }

        if (!Enum.TryParse<LessonPhase>(phaseToken, ignoreCase: true, out var phase))
        {
            throw new InvalidOperationException($"Unknown lesson phase '{phaseToken}'");
        }

        Phase = phase;
        Line = obj.Value<string>("line");
        Origin = obj.Value<string>("origin");
        Story = obj.Value<string>("story");

        var itemsToken = obj["items"];
        if (itemsToken is JArray arr)
        {
            Items = arr.Values<string>().Where(s => !string.IsNullOrWhiteSpace(s)).Select(s => s!).ToList();
        }
    }
}

public class Lesson
{
    private static readonly SlugHelper Slugger = new();

    [JsonProperty("id")]
    public string Id { get; set; }

    [JsonProperty("title")]
    public string Title { get; set; }

    [JsonProperty("nickname")]
    public string Nickname { get; set; }

    [JsonProperty("level")]
    public string Level { get; set; }

    [JsonProperty("unit")]
    public int Unit { get; set; }

    [JsonProperty("lesson_number")]
    public int LessonNumber { get; set; }

    [JsonProperty("tags")]
    public List<string> Tags { get; set; }

    [JsonProperty("steps")]
    public List<LessonStep> Steps { get; set; }

    [JsonProperty("notes")]
    public string? Notes { get; set; }

    [JsonProperty("notes_alt_variant")]
    public string? NotesAltVariant { get; set; }

    [JsonProperty("source_files")]
    public List<string> SourceFiles { get; set; }

    public Lesson(JObject obj, HashSet<string> sourceFiles)
    {
        Title = obj.Value<string>("title")?.Trim() ?? throw new InvalidOperationException("Lesson requires title");
        Level = Cefr.Normalize(obj.Value<string>("level"));
        Unit = obj.Value<int?>("unit") ?? 0;
        LessonNumber = obj.Value<int?>("lesson_number") ?? 0;
        Nickname = obj.Value<string>("nickname")?.Trim() ?? Slugger.GenerateSlug(Title);
        Tags = NormalizeTags(obj["tags"]);
        Steps = NormalizeSteps(obj["steps"]);
        Notes = obj.Value<string>("notes")?.Trim();
        NotesAltVariant = obj.Value<string>("notes_alt_variant")?.Trim();
        SourceFiles = sourceFiles.OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList();
        Id = obj.Value<string>("id")?.Trim() ?? BuildId(Unit, Title);
    }

    public Lesson(string id,
        string title,
        string nickname,
        string level,
        int unit,
        int lessonNumber,
        IEnumerable<string> tags,
        IEnumerable<LessonStep> steps,
        string? notes,
        string? notesAlt,
        IEnumerable<string> sourceFiles)
    {
        Id = id;
        Title = title;
        Nickname = string.IsNullOrWhiteSpace(nickname) ? Slugger.GenerateSlug(title) : nickname;
        Level = Cefr.Normalize(level);
        Unit = unit;
        LessonNumber = lessonNumber;
        Tags = tags?.Where(t => !string.IsNullOrWhiteSpace(t)).Select(t => t.Trim()).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(t => t, StringComparer.OrdinalIgnoreCase).ToList() ?? new List<string>();
        Steps = steps?.ToList() ?? new List<LessonStep>();
        Notes = notes;
        NotesAltVariant = notesAlt;
        SourceFiles = sourceFiles?.Distinct().OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList() ?? new List<string>();
    }

    public static string BuildId(int unit, string title)
    {
        var slug = Slugger.GenerateSlug(title);
        return $"mmspanish__grammar_{unit:000}_{slug}";
    }

    private static List<string> NormalizeTags(JToken? token)
    {
        if (token is JArray arr)
        {
            return arr.Values<string>()
                .Where(t => !string.IsNullOrWhiteSpace(t))
                .Select(t => t!.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(t => t, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        return new List<string>();
    }

    private static List<LessonStep> NormalizeSteps(JToken? token)
    {
        var steps = new List<LessonStep>();
        if (token is JArray arr)
        {
            foreach (var item in arr.OfType<JObject>())
            {
                steps.Add(new LessonStep(item));
            }
        }

        return steps;
    }
}

public class Vocabulary
{
    [JsonProperty("id")]
    public string Id { get; set; }

    [JsonProperty("spanish")]
    public string Spanish { get; set; }

    [JsonProperty("pos")]
    public string Pos { get; set; }

    [JsonProperty("gender")]
    public string? Gender { get; set; }

    [JsonProperty("english_gloss")]
    public string EnglishGloss { get; set; }

    [JsonProperty("definition")]
    public string Definition { get; set; }

    [JsonProperty("origin")]
    public string? Origin { get; set; }

    [JsonProperty("story")]
    public string? Story { get; set; }

    [JsonProperty("examples")]
    public List<Dictionary<string, string>> Examples { get; set; }

    [JsonProperty("level")]
    public string Level { get; set; }

    [JsonProperty("tags")]
    public List<string> Tags { get; set; }

    [JsonProperty("notes")]
    public string? Notes { get; set; }

    [JsonProperty("notes_alt_variant")]
    public string? NotesAltVariant { get; set; }

    [JsonProperty("source_files")]
    public List<string> SourceFiles { get; set; }

    public Vocabulary(JObject obj, HashSet<string> sourceFiles)
    {
        Spanish = obj.Value<string>("spanish")?.Trim() ?? throw new InvalidOperationException("Vocabulary requires spanish");
        Pos = NormalizePos(obj.Value<string>("pos"));
        Gender = NormalizeGender(obj["gender"]);
        EnglishGloss = obj.Value<string>("english_gloss")?.Trim() ?? string.Empty;
        Definition = obj.Value<string>("definition")?.Trim() ?? string.Empty;
        Origin = NormalizeNullableString(obj["origin"]);
        Story = NormalizeNullableString(obj["story"]);
        Examples = NormalizeExamples(obj["examples"]);
        Level = Cefr.Normalize(obj.Value<string>("level"));
        Tags = NormalizeTags(obj["tags"]);
        Notes = obj.Value<string>("notes")?.Trim();
        NotesAltVariant = obj.Value<string>("notes_alt_variant")?.Trim();
        SourceFiles = sourceFiles.OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList();
        var genderPart = Gender ?? "null";
        Id = obj.Value<string>("id")?.Trim() ?? BuildId(Spanish, Pos, genderPart);
    }

    public Vocabulary(string id,
        string spanish,
        string pos,
        string? gender,
        string english,
        string definition,
        string? origin,
        string? story,
        IEnumerable<Dictionary<string, string>> examples,
        string level,
        IEnumerable<string> tags,
        string? notes,
        string? notesAlt,
        IEnumerable<string> sourceFiles)
    {
        Id = id;
        Spanish = spanish;
        Pos = NormalizePos(pos);
        Gender = NormalizeGender(gender);
        EnglishGloss = english;
        Definition = definition;
        Origin = origin;
        Story = story;
        Examples = examples.Select(e => new Dictionary<string, string>(e, StringComparer.OrdinalIgnoreCase)).ToList();
        Level = Cefr.Normalize(level);
        Tags = tags?.Where(t => !string.IsNullOrWhiteSpace(t)).Select(t => t.Trim()).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(t => t, StringComparer.OrdinalIgnoreCase).ToList() ?? new List<string>();
        Notes = notes;
        NotesAltVariant = notesAlt;
        SourceFiles = sourceFiles?.Distinct().OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList() ?? new List<string>();
    }

    public static string BuildId(string spanish, string pos, string gender)
    {
        var data = Encoding.UTF8.GetBytes($"{spanish}|{pos}|{gender}");
        var hash = MurmurHash.Create128().ComputeHash(data);
        return $"mmspanish__vocab_{Convert.ToHexString(hash).ToLowerInvariant()}";
    }

    private static string NormalizePos(string? pos)
    {
        if (string.IsNullOrWhiteSpace(pos))
        {
            return "expr";
        }

        var token = pos.Trim().ToLowerInvariant();
        return token switch
        {
            "noun" or "verb" or "adj" or "adv" or "prep" or "det" or "pron" or "conj" or "expr" => token,
            "adjective" => "adj",
            "adverb" => "adv",
            "expression" => "expr",
            "article" => "det",
            _ => token
        };
    }

    private static string? NormalizeGender(object? gender)
    {
        if (gender is null)
        {
            return null;
        }

        var token = gender.ToString()?.Trim().ToLowerInvariant();
        if (string.IsNullOrEmpty(token))
        {
            return null;
        }

        return token switch
        {
            "m" or "masculino" or "masculine" => "masculine",
            "f" or "femenino" or "feminine" => "feminine",
            _ => null
        };
    }

    private static string? NormalizeGender(JToken? token)
        => NormalizeGender(token?.Type == JTokenType.Null ? null : token?.ToString());

    private static string? NormalizeNullableString(JToken? token)
    {
        if (token is null || token.Type == JTokenType.Null)
        {
            return null;
        }

        var text = token.ToString().Trim();
        return string.IsNullOrWhiteSpace(text) ? null : text;
    }

    private static List<Dictionary<string, string>> NormalizeExamples(JToken? token)
    {
        var list = new List<Dictionary<string, string>>();
        if (token is JArray arr)
        {
            foreach (var item in arr)
            {
                if (item is JObject obj)
                {
                    var es = obj.Value<string>("es") ?? obj.Value<string>("spanish") ?? string.Empty;
                    var en = obj.Value<string>("en") ?? obj.Value<string>("english") ?? string.Empty;
                    if (!string.IsNullOrWhiteSpace(es) || !string.IsNullOrWhiteSpace(en))
                    {
                        list.Add(new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                        {
                            ["es"] = es.Trim(),
                            ["en"] = en.Trim()
                        });
                    }
                }
                else if (item.Type == JTokenType.String)
                {
                    var text = item.ToString();
                    if (!string.IsNullOrWhiteSpace(text))
                    {
                        list.Add(new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                        {
                            ["es"] = text.Trim(),
                            ["en"] = text.Trim()
                        });
                    }
                }
            }
        }

        return list;
    }

    private static List<string> NormalizeTags(JToken? token)
    {
        if (token is JArray arr)
        {
            return arr.Values<string>()
                .Where(t => !string.IsNullOrWhiteSpace(t))
                .Select(t => t!.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(t => t, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        return new List<string>();
    }
}

public record Reject(string SourceFile, string Reason, string Snippet);

public record CandidateResult(
    string Kind,
    JObject Data,
    DateTime Modified,
    HashSet<string> SourceFiles,
    string Key);

public static class ModelHelpers
{
    public static Lesson ToLesson(CandidateResult candidate)
    {
        return new Lesson(candidate.Data, candidate.SourceFiles);
    }

    public static Vocabulary ToVocabulary(CandidateResult candidate)
    {
        return new Vocabulary(candidate.Data, candidate.SourceFiles);
    }

    public static string LessonKey(JObject obj)
    {
        var title = obj.Value<string>("title")?.Trim() ?? string.Empty;
        var unit = obj.Value<int?>("unit");
        var lessonNumber = obj.Value<int?>("lesson_number");
        var nickname = obj.Value<string>("nickname")?.Trim() ?? string.Empty;
        if (unit.HasValue && lessonNumber.HasValue)
        {
            return $"lesson::{title.ToLowerInvariant()}::{unit.Value:D4}::{lessonNumber.Value:D4}";
        }

        return $"lesson::{title.ToLowerInvariant()}::{nickname.ToLowerInvariant()}";
    }

    public static string VocabularyKey(JObject obj)
    {
        var spanish = obj.Value<string>("spanish")?.Trim().ToLowerInvariant() ?? string.Empty;
        var pos = obj.Value<string>("pos")?.Trim().ToLowerInvariant() ?? string.Empty;
        var gender = obj.Value<string>("gender")?.Trim().ToLowerInvariant() ?? "null";
        return $"vocab::{spanish}::{pos}::{gender}";
    }
}
