defmodule CodexRebuilder.Normalizer do
  @moduledoc """
  Classifies parsed data structures as lessons or vocabulary and normalises
  them into canonical maps compliant with the JSON schemas.
  """

  alias CodexRebuilder.ID

    @type classification :: {:lesson | :vocab, map()}

  @spec classify_and_normalize(any(), binary(), non_neg_integer()) ::
          {[classification()], [map()]}
  def classify_and_normalize(data, path, mtime)

  def classify_and_normalize(list, path, mtime) when is_list(list) do
    Enum.reduce(list, {[], []}, fn item, {acc, rejects} ->
      {items, rej} = classify_and_normalize(item, path, mtime)
      {acc ++ items, rejects ++ rej}
    end)
  end

  def classify_and_normalize(map, path, mtime) when is_map(map) do
    map = stringify_keys(map)
    base = Map.put(map, "source_files", uniq_list([path | List.wrap(map["source_files"]) ]))

    cond do
      lesson?(base) and vocab?(base) ->
        {lesson_map, l_rejects} = build_lesson(base, path, mtime)
        {vocab_map, v_rejects} = build_vocab(base, path, mtime)
        {Enum.reject([{:lesson, lesson_map}, {:vocab, vocab_map}], &is_nil/1), l_rejects ++ v_rejects}

      lesson?(base) ->
        {lesson_map, rejects} = build_lesson(base, path, mtime)
        {[{:lesson, lesson_map}], rejects}

      vocab?(base) ->
        {vocab_map, rejects} = build_vocab(base, path, mtime)
        {[{:vocab, vocab_map}], rejects}

      true ->
        reject = %{reason: :unknown_payload, data: base, path: path}
        {[], [reject]}
    end
  end

  def classify_and_normalize(_other, path, _mtime) do
    {[], [%{reason: :unsupported_payload, path: path}]}
  end

  defp lesson?(map), do: Map.has_key?(map, "steps") or Map.has_key?(map, "lesson_number")
  defp vocab?(map), do: Map.has_key?(map, "spanish") or Map.has_key?(map, "english_gloss")

  defp build_lesson(map, path, mtime) do
    title = coalesce_string(map["title"], map["name"], "Lesson")
    nickname = coalesce_string(map["nickname"], map["nikname"], ID.slug(title))
    unit = normalize_int(map["unit"], 9999)
    lesson_number = normalize_int(map["lesson_number"], 9999)
    level = infer_level(map["level"], path)
    tags = uniq_list(map["tags"] || [])

    steps =
      map
      |> Map.get("steps", [])
      |> Enum.map(&normalize_step/1)
      |> Enum.reject(&is_nil/1)

    lesson = %{
      "id" => lesson_id(map, title, unit),
      "title" => title,
      "nickname" => nickname,
      "level" => level,
      "unit" => unit,
      "lesson_number" => lesson_number,
      "tags" => steps_tags(map, tags),
      "steps" => steps,
      "source_files" => uniq_list(map["source_files"] || [])
    }

    notes = normalize_notes(map["notes"])
    lesson = maybe_put_note(lesson, notes)
    {Map.put(lesson, "__meta", %{mtime: mtime, path: path}), []}
  end

  defp steps_tags(map, tags) do
    extra = map |> Map.get("tags", []) |> List.wrap()
    uniq_list(tags ++ extra)
  end

  defp build_vocab(map, path, mtime) do
    spanish = coalesce_string(map["spanish"], map["word"], "")
    pos = map["pos"] || map["part_of_speech"]
    english = coalesce_string(map["english_gloss"], map["english"], "")
    definition = coalesce_string(map["definition"], map["meaning"], "")
    level = infer_level(map["level"], path)
    tags = uniq_list(map["tags"] || [])

    examples =
      map
      |> Map.get("examples", [])
      |> Enum.map(&normalize_example/1)
      |> Enum.reject(&is_nil/1)

    norm_pos = normalize_pos(pos)

    vocab = %{
      "id" => ID.vocab_id(spanish, norm_pos, map["gender"]),
      "spanish" => spanish,
      "pos" => norm_pos,
      "gender" => normalize_gender(map["gender"]),
      "english_gloss" => english,
      "definition" => definition,
      "origin" => map |> Map.get("origin"),
      "story" => map |> Map.get("story"),
      "examples" => examples,
      "level" => level,
      "tags" => tags,
      "source_files" => uniq_list(map["source_files"] || [])
    }

    notes = normalize_notes(map["notes"]) 
    vocab = maybe_put_note(vocab, notes)
    {Map.put(vocab, "__meta", %{mtime: mtime, path: path}), []}
  end

  defp normalize_step(step) when is_map(step) do
    step = stringify_keys(step)

    phase =
      step
      |> Map.get("phase")
      |> to_string()
      |> String.downcase()

    case phase do
      "english_anchor" -> build_step(step, "english_anchor")
      "system_logic" -> build_step(step, "system_logic")
      "meaning_depth" -> build_step(step, "meaning_depth")
      "spanish_entry" -> build_step(step, "spanish_entry")
      "examples" -> build_step(step, "examples")
      _ -> nil
    end
  end

  defp normalize_step(_), do: nil

  defp build_step(step, phase) do
    items =
      step
      |> Map.get("items", [])
      |> List.wrap()
      |> Enum.map(&to_string/1)

    %{
      "phase" => phase,
      "line" => step["line"],
      "origin" => step["origin"],
      "story" => step["story"],
      "items" => items
    }
  end

  defp normalize_example(%{"es" => es, "en" => en}) do
    %{"es" => to_string(es), "en" => to_string(en)}
  end

  defp normalize_example(%{"es" => es} = map) do
    %{"es" => to_string(es), "en" => to_string(Map.get(map, "en", es))}
  end

  defp normalize_example(value) when is_binary(value) do
    %{"es" => value, "en" => value}
  end

  defp normalize_example(_), do: nil

  defp normalize_pos(nil), do: "expr"
  defp normalize_pos(pos) when is_binary(pos), do: String.downcase(pos)
  defp normalize_pos(pos) when is_atom(pos), do: Atom.to_string(pos)

  defp normalize_gender(nil), do: nil
  defp normalize_gender(gender) when gender in ["masculine", "feminine"], do: gender
  defp normalize_gender(gender) when is_binary(gender), do: String.downcase(gender)
  defp normalize_gender(_), do: nil

  defp normalize_notes(nil), do: nil
  defp normalize_notes(notes) when is_binary(notes), do: String.trim(notes)
  defp normalize_notes(notes) when is_list(notes), do: Enum.join(Enum.map(notes, &to_string/1), "\n")
  defp normalize_notes(other), do: inspect(other)

  defp uniq_list(list) do
    list
    |> List.wrap()
    |> Enum.map(&to_string/1)
    |> Enum.uniq()
  end

  defp stringify_keys(map) do
    map
    |> Enum.map(fn {k, v} -> {to_string(k), v} end)
    |> Map.new()
  end

  defp coalesce_string(nil, nil, default), do: default
  defp coalesce_string(nil, other, _default), do: to_string(other)
  defp coalesce_string(value, _other, _default), do: to_string(value)

  defp normalize_int(nil, default), do: default
  defp normalize_int(value, default) when is_integer(value), do: value
  defp normalize_int(value, default) do
    case Integer.parse(to_string(value)) do
      {int, _} -> int
      :error -> default
    end
  end

  defp infer_level(value, path) do
    cond do
      value && value in ~w(A1 A2 B1 B2 C1 C2 UNSET) -> value
      is_binary(value) ->
        value
        |> String.upcase()
        |> normalize_level_from_path(path)

      true ->
        normalize_level_from_path("UNSET", path)
    end
  end

  defp normalize_level_from_path(level, path) do
    case Regex.run(~r/(A1|A2|B1|B2|C1|C2)/i, to_string(path)) do
      [match] -> String.upcase(match)
      _ -> level
    end
  end

  defp lesson_id(map, title, unit) do
    Map.get(map, "id") || ID.lesson_id(unit, title)
  end

  defp maybe_put_note(map, nil), do: map
  defp maybe_put_note(map, ""), do: map
  defp maybe_put_note(map, note), do: Map.put(map, "notes", note)
end
