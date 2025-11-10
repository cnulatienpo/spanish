defmodule CodexRebuilder.CLI do
  @moduledoc """
  Mix entry point for rebuilding the corpus.
  """

  alias CodexRebuilder
  alias NimbleOptions, as: NO

  @schema [
    check: [type: :boolean, default: false],
    write: [type: :boolean, default: true],
    strict: [type: :boolean, default: false],
    root: [type: :string, default: File.cwd!()]
  ]

  @doc """
  Mix alias entry. Accepts the CLI argv.
  """
  def run(args) do
    Mix.Task.run("app.start")

    with {:ok, opts} <- parse_args(args),
         {:ok, report} <- CodexRebuilder.run(opts) do
      Mix.shell().info(report.console)

      if opts.write do
        Mix.shell().info("✨ Canonical JSONs written to build/canonical/")
      else
        Mix.shell().info("ℹ️  Checked corpus without writing outputs")
      end

      if report.strict_failure do
        Mix.raise("strict mode failure")
      end

      :ok
    else
      {:error, :invalid_args, message} -> Mix.raise(message)
      {:error, reason} -> Mix.raise("codex.rebuild failed: #{inspect(reason)}")
    end
  end

  defp parse_args(args) do
    {opts, _, _} = OptionParser.parse(args, switches: [check: :boolean, write: :boolean, strict: :boolean, root: :string])

    opts =
      opts
      |> Map.new()
      |> adjust_write_check()

    case NO.validate(opts, @schema) do
      {:ok, validated} -> {:ok, validated}
      {:error, %NO.ValidationError{message: msg}} -> {:error, :invalid_args, msg}
    end
  end

  defp adjust_write_check(%{check: true} = opts), do: Map.put(opts, :write, false)
  defp adjust_write_check(opts), do: opts
end
