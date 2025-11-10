defmodule CodexRebuilder.Validator do
  @moduledoc """
  Validates normalised entries against the JSON schemas.
  """

  alias CodexRebuilder.Schemas
  alias ExJsonSchema.Validator

  @spec validate_lessons([map()]) :: {[map()], [map()]}
  def validate_lessons(entries) do
    validate(entries, Schemas.load(:lesson), :lesson)
  end

  @spec validate_vocab([map()]) :: {[map()], [map()]}
  def validate_vocab(entries) do
    validate(entries, Schemas.load(:vocab), :vocab)
  end

  defp validate(entries, schema, type) do
    Enum.reduce(entries, {[], []}, fn entry, {valid, rejects} ->
      cleaned = Map.drop(entry, ["__meta"])

      case Validator.validate(schema, cleaned) do
        :ok -> {[cleaned | valid], rejects}
        {:error, errors} ->
          reject = %{reason: :schema_error, type: type, errors: errors, data: cleaned}
          {valid, [reject | rejects]}
      end
    end)
  end
end
