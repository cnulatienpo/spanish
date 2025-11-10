using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace CodexFixer;

public static class IO
{
    private static readonly JsonSerializer Serializer = JsonSerializer.Create(new JsonSerializerSettings
    {
        NullValueHandling = NullValueHandling.Ignore,
        Formatting = Formatting.Indented
    });

    public static IEnumerable<string> EnumerateContentFiles(string root)
    {
        if (!Directory.Exists(root))
        {
            return Enumerable.Empty<string>();
        }

        return Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories);
    }

    public static string ReadAllText(string path)
        => File.ReadAllText(path);

    public static DateTime GetModifiedTime(string path)
    {
        return File.GetLastWriteTimeUtc(path);
    }

    public static void EnsureDirectory(string path)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
        {
            Directory.CreateDirectory(dir);
        }
    }

    public static void WriteJsonArray<T>(string path, IEnumerable<T> items)
    {
        EnsureDirectory(path);
        var token = JToken.FromObject(items, Serializer);
        token = SortToken(token);
        using var writer = new StreamWriter(path, false, new UTF8Encoding(false));
        using var jsonWriter = new JsonTextWriter(writer)
        {
            Formatting = Formatting.Indented,
            Indentation = 2
        };
        token.WriteTo(jsonWriter);
    }

    public static JArray ToJArray<T>(IEnumerable<T> items)
    {
        var token = JToken.FromObject(items, Serializer);
        if (token is JArray arr)
        {
            return (JArray)SortToken(arr);
        }

        return new JArray();
    }

    private static JToken SortToken(JToken token)
    {
        switch (token)
        {
            case JObject obj:
                var props = obj.Properties()
                    .OrderBy(p => p.Name, StringComparer.Ordinal)
                    .Select(p => new JProperty(p.Name, SortToken(p.Value)))
                    .ToList();
                var sorted = new JObject();
                foreach (var prop in props)
                {
                    sorted.Add(prop);
                }

                return sorted;
            case JArray array:
                var arr = new JArray();
                foreach (var item in array)
                {
                    arr.Add(SortToken(item));
                }

                return arr;
            default:
                return token;
        }
    }

    public static void WriteAudit(string path, string content)
    {
        EnsureDirectory(path);
        File.WriteAllText(path, content, new UTF8Encoding(false));
    }
}
