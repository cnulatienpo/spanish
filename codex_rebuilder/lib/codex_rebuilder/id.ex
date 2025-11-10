defmodule CodexRebuilder.ID do
  @moduledoc """
  Generates stable identifiers for lessons and vocabulary entries.
  """

  def vocab_id(spanish, pos, gender) do
    span = normalize(spanish)
    pos = normalize(pos)
    gender = normalize(gender) || "null"
    seed = Enum.join([span, pos, gender], "|")

    "mmspanish__vocab_" <> digest(seed)
  end

  def lesson_id(unit, title) do
    unit = unit || 0
    unit_str = unit |> Integer.to_string() |> String.pad_leading(3, "0")
    "mmspanish__grammar_#{unit_str}_#{slug(title)}"
  end

  def slug(title) do
    title
    |> to_string()
    |> String.downcase()
    |> String.replace(~r/[^a-z0-9]+/u, "-")
    |> String.trim("-")
  end

  defp digest(seed) do
    :crypto.hash(:sha256, seed)
    |> Base.encode16(case: :lower)
    |> binary_part(0, 16)
  end

  defp normalize(nil), do: nil
  defp normalize(value) when is_binary(value), do: String.downcase(String.trim(value))
  defp normalize(value), do: value |> to_string() |> String.downcase()
end
