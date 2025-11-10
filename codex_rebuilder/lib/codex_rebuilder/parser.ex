defmodule CodexRebuilder.Parser do
  @moduledoc """
  Extracts JSON fragments from raw text and attempts to decode them using
  a tolerant JSON loader.
  """

  @type fragment :: %{data: any(), raw: binary()}

  @spec extract_json(binary()) :: {[fragment()], [map()]}
  def extract_json(text) when is_binary(text) do
    fragments = collect_fragments(text)

    Enum.reduce(fragments, {[], []}, fn raw, {ok, rejects} ->
      case decode_relaxed(raw) do
        {:ok, data} -> {[%{data: data, raw: raw} | ok], rejects}
        {:error, reason} ->
          reject = %{reason: reason, raw: raw}
          {ok, [reject | rejects]}
      end
    end)
  end

  @spec try_parse(binary()) :: {:ok, any()} | :error
  def try_parse(text) do
    case decode_relaxed(text) do
      {:ok, data} -> {:ok, data}
      {:error, _} -> :error
    end
  end

  defp collect_fragments(text) do
    size = byte_size(text)
    do_collect(text, 0, size, [], [])
    |> Enum.reverse()
  end

  defp do_collect(_text, index, size, _stack, acc) when index >= size, do: acc

  defp do_collect(text, index, size, stack, acc) do
    <<_::binary-size(index), char::utf8, _::binary>> = text

    cond do
      char in [?{, ?[] ->
        do_collect(text, index + 1, size, [{char, index} | stack], acc)

      char == ?} ->
        handle_close(text, index, size, stack, acc, ?{)

      char == ?] ->
        handle_close(text, index, size, stack, acc, ?[)

      true ->
        do_collect(text, index + 1, size, stack, acc)
    end
  end

  defp handle_close(text, index, size, [{open_char, start} | rest], acc, expected)
       when open_char == expected do
    frag_len = index - start + 1
    fragment = binary_part(text, start, frag_len)
    new_acc =
      if rest == [] do
        [fragment | acc]
      else
        acc
      end

    do_collect(text, index + 1, size, rest, new_acc)
  end

  defp handle_close(text, index, size, stack, acc, _expected) do
    do_collect(text, index + 1, size, stack, acc)
  end

  defp decode_relaxed(text) do
    cleaned =
      text
      |> strip_bom()
      |> repair_common_issues()

    case Jason.decode(cleaned) do
      {:ok, value} -> {:ok, value}
      error -> error
    end
  rescue
    _ -> {:error, :invalid_json}
  end

  defp strip_bom("\uFEFF" <> rest), do: rest
  defp strip_bom(text), do: text

  defp repair_common_issues(text) do
    text
    |> remove_trailing_commas()
    |> quote_bare_keys()
    |> normalize_single_quotes()
  end

  defp remove_trailing_commas(text) do
    Regex.replace(~r/,\s*(\}|\])/, text, "\\1")
  end

  defp quote_bare_keys(text) do
    Regex.replace(~r/([\{,]\s*)([A-Za-z0-9_]+)\s*:/, text, "\\1\"\\2\" :")
  end

  defp normalize_single_quotes(text) do
    Regex.replace(~r/'([^'\\]*(?:\\.[^'\\]*)*)'/, text, "\"\\1\"")
  end
end
