defmodule CodexRebuilder.Schemas do
  @moduledoc """
  Loads and caches JSON schemas used for validation.
  """

  @schemas %{
    lesson: "lesson.schema.json",
    vocab: "vocab.schema.json"
  }

  @spec load(atom()) :: ExJsonSchema.Schema.Root.t()
  def load(type) do
    with {:ok, schema} <- Map.fetch(@schemas, type) do
      schema
      |> priv_path()
      |> File.read!()
      |> Jason.decode!()
      |> ExJsonSchema.Schema.resolve()
    else
      :error -> raise ArgumentError, "unknown schema type #{inspect(type)}"
    end
  end

  defp priv_path(file) do
    :codex_rebuilder
    |> :code.priv_dir()
    |> Path.join("schemas")
    |> Path.join(file)
  end
end
