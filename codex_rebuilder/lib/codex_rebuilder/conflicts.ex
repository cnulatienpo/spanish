defmodule CodexRebuilder.Conflicts do
  @moduledoc """
  Heals Git merge conflicts embedded in text by selecting or merging
  the conflicting variants.
  """

  alias CodexRebuilder.Merger
  alias CodexRebuilder.Parser

  @conflict ~r/<<<<<<<.*?\n(?<left>.*?)(?:\n)?=======\n(?<right>.*?)(?:\n)?>>>>>>>.*?(?:\n|$)/s

  @type heal_result :: %{segments: [binary()], healed: non_neg_integer(), rejects: [map()]}

  @spec heal(binary()) :: heal_result
  def heal(text) do
    do_heal(text, [], 0, [])
  end

  defp do_heal(text, segments, healed, rejects) do
    case Regex.run(@conflict, text, capture: :all, return: :index) do
      nil ->
        final_segments =
          case text do
            "" -> segments
            _ -> [text | segments]
          end

        %{segments: Enum.reverse(final_segments), healed: healed, rejects: rejects}

      [{start, len}, {left_start, left_len}, {right_start, right_len}] ->
        prefix = binary_part(text, 0, start)
        left = text |> binary_part(left_start, left_len) |> String.trim()
        right = text |> binary_part(right_start, right_len) |> String.trim()
        rest_index = start + len
        rest = binary_part(text, rest_index, byte_size(text) - rest_index)

        {resolved, new_rejects} = resolve_conflict(left, right)

        new_segments =
          segments
          |> maybe_cons(prefix)
          |> maybe_cons(resolved)

        do_heal(rest, new_segments, healed + 1, new_rejects ++ rejects)
    end
  end

  defp maybe_cons(list, ""), do: list
  defp maybe_cons(list, nil), do: list
  defp maybe_cons(list, segment), do: [segment | list]

  defp resolve_conflict(left, right) do
    with {:ok, parsed_left} <- Parser.try_parse(left),
         {:ok, parsed_right} <- Parser.try_parse(right) do
      {merged, notes} = Merger.deep_merge(parsed_left, parsed_right, nil, nil)
      json = Jason.encode!(maybe_attach_notes(merged, notes))
      {json, []}
    else
      :error -> choose_side(left, right)
      {:ok, _} -> choose_side(left, right)
      _ -> choose_side(left, right)
    end
  rescue
    _ -> choose_side(left, right)
  end

  defp choose_side(left, right) do
    case {Parser.try_parse(left), Parser.try_parse(right)} do
      {{:ok, _}, :error} -> {left, []}
      {:error, {:ok, _}} -> {right, []}
      {{:ok, _}, {:ok, _}} -> {left, []}
      _ ->
        reject = %{reason: :unhealed_conflict, left: left, right: right}
        {left, [reject]}
    end
  end

  defp maybe_attach_notes(map, []), do: map
  defp maybe_attach_notes(map, notes) when is_map(map) do
    note_text = Enum.join(notes, "\n")
    Map.update(map, "notes", note_text, fn existing ->
      cond do
        existing == note_text -> existing
        existing in [nil, ""] -> note_text
        true -> existing <> "\n" <> note_text
      end
    end)
  end
  defp maybe_attach_notes(value, _notes), do: value
end
