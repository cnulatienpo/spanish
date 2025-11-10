defmodule CodexRebuilder.Merger do
  @moduledoc """
  Provides deep merge semantics for lesson and vocabulary records and
  utilities for deduplicating and sorting.
  """

  @text_fields ["definition", "origin", "story"]

  @spec deep_merge(map(), map(), integer() | nil, integer() | nil) :: {map(), [String.t()]}
  def deep_merge(a, b, mtime_a, mtime_b) do
    {merged, notes} = do_deep_merge(a, b, mtime_a, mtime_b, [])
    {merged, Enum.reverse(notes)}
  end

  defp do_deep_merge(%{} = a, %{} = b, mtime_a, mtime_b, path) do
    keys = Map.keys(a) ++ Map.keys(b) |> Enum.uniq()

    Enum.reduce(keys, {%{}, []}, fn key, {acc, notes} ->
      value_a = Map.get(a, key)
      value_b = Map.get(b, key)

      case {value_a, value_b} do
        {nil, _} -> {Map.put(acc, key, value_b), notes}
        {_, nil} -> {Map.put(acc, key, value_a), notes}
        _ ->
          {value, additions} = do_deep_merge(value_a, value_b, mtime_a, mtime_b, [key | path])
          {Map.put(acc, key, value), additions ++ notes}
      end
    end)
  end

  defp do_deep_merge(list_a, list_b, _mtime_a, _mtime_b, _path) when is_list(list_a) and is_list(list_b) do
    {merge_lists(list_a, list_b), []}
  end

  defp do_deep_merge(value_a, value_b, mtime_a, mtime_b, path) when is_binary(value_a) and is_binary(value_b) do
    key = List.first(path)

    cond do
      key in @text_fields and value_a != value_b ->
        {merge_text(value_a, value_b), []}

      true ->
        {winner, loser} = select_scalar(value_a, value_b, mtime_a, mtime_b)
        {winner, build_note(path, loser)}
    end
  end

  defp do_deep_merge(value_a, value_b, mtime_a, mtime_b, path) do
    {winner, loser} = select_scalar(value_a, value_b, mtime_a, mtime_b)
    {winner, build_note(path, loser)}
  end

  defp merge_lists(a, b) do
    a ++ b
    |> Enum.reduce({[], MapSet.new()}, fn item, {acc, seen} ->
      key = list_item_key(item)

      if MapSet.member?(seen, key) do
        {acc, seen}
      else
        {[item | acc], MapSet.put(seen, key)}
      end
    end)
    |> elem(0)
    |> Enum.reverse()
  end

  defp list_item_key(%{"es" => es, "en" => en}) do
    {"example", normalize_string(es), normalize_string(en)}
  end

  defp list_item_key(item) when is_binary(item), do: {"string", normalize_string(item)}
  defp list_item_key(item), do: {"other", item}

  defp normalize_string(str) do
    str
    |> to_string()
    |> String.trim()
    |> String.downcase()
  end

  defp merge_text(a, b) do
    [String.trim(a), String.trim(b)]
    |> Enum.uniq()
    |> case do
      [only] -> only
      list -> Enum.join(list, "\n\n— MERGED VARIANT —\n\n")
    end
  end

  defp select_scalar(a, b, mtime_a, mtime_b) do
    cond do
      a == b -> {a, nil}
      mtime_a && mtime_b && mtime_a > mtime_b -> {a, b}
      mtime_a && mtime_b && mtime_b > mtime_a -> {b, a}
      byte_size(to_string(a)) >= byte_size(to_string(b)) -> {a, b}
      true -> {b, a}
    end
  end

  defp build_note(path, nil), do: []
  defp build_note(path, value) do
    key_path = Enum.reverse(path)

    cond do
      Enum.any?(key_path, &(&1 == "__meta")) -> []
      true -> ["alt variant for #{Enum.join(key_path, ".")}: #{inspect(value)}"]
    end
  end

  @doc """
  Deduplicate lesson entries by merging records with matching keys.
  """
  def dedupe_lessons(lessons) do
    dedupe_by(lessons, &lesson_key/1)
  end

  @doc """
  Deduplicate vocabulary entries by merging records with matching keys.
  """
  def dedupe_vocab(vocabs) do
    dedupe_by(vocabs, &vocab_key/1)
  end

  defp dedupe_by(entries, key_fun) do
    {merged, duplicates} =
      Enum.reduce(entries, {%{}, 0}, fn entry, {acc, dup_count} ->
        key = key_fun.(entry)

        case Map.fetch(acc, key) do
          {:ok, existing} ->
            mtime_a = get_in(existing, ["__meta", :mtime])
            mtime_b = get_in(entry, ["__meta", :mtime])
            {combined, notes} = deep_merge(existing, entry, mtime_a, mtime_b)
            merged = combined |> attach_notes(notes) |> merge_sources(entry)
            {Map.put(acc, key, merged), dup_count + 1}

          :error ->
            {Map.put(acc, key, entry), dup_count}
        end
      end)

    {Map.values(merged), duplicates}
  end

  defp merge_sources(a, b) do
    files = ((a["source_files"] || []) ++ (b["source_files"] || [])) |> Enum.uniq()
    merged = Map.put(a, "source_files", files)

    case Map.get(b, "notes") do
      nil -> merged
      note ->
        Map.update(merged, "notes", note, fn existing ->
          cond do
            existing in [nil, ""] -> note
            existing == note -> note
            true -> existing <> "\n" <> note
          end
        end)
    end
  end

  defp attach_notes(map, []), do: map

  defp attach_notes(map, notes) when is_map(map) do
    note_text = Enum.join(notes, "\n")

    Map.update(map, "notes", note_text, fn existing ->
      cond do
        existing in [nil, ""] -> note_text
        existing == note_text -> note_text
        true -> existing <> "\n" <> note_text
      end
    end)
  end

  defp attach_notes(value, _notes), do: value

  defp lesson_key(map) do
    unit = Map.get(map, "unit")
    lesson_number = Map.get(map, "lesson_number")
    title = String.downcase(Map.get(map, "title", ""))
    nickname = String.downcase(Map.get(map, "nickname", ""))

    if unit && lesson_number do
      "#{title}|#{unit}|#{lesson_number}"
    else
      "#{title}|#{nickname}"
    end
  end

  defp vocab_key(map) do
    spanish = map |> Map.get("spanish", "") |> String.downcase()
    pos = map |> Map.get("pos", "") |> String.downcase()
    gender = map |> Map.get("gender")
    "#{spanish}|#{pos}|#{gender || "null"}"
  end

  def sort(entries) do
    order = %{"A1" => 1, "A2" => 2, "B1" => 3, "B2" => 4, "C1" => 5, "C2" => 6, "UNSET" => 7}

    Enum.sort_by(entries, fn entry ->
      level = Map.get(entry, "level", "UNSET")
      unit = Map.get(entry, "unit") || 9999
      lesson_number = Map.get(entry, "lesson_number") || 9999
      {Map.get(order, level, 7), unit, lesson_number, Map.get(entry, "id")}
    end)
  end
end
