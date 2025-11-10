defmodule CodexRebuilder.MixProject do
  use Mix.Project

  def project do
    [
      app: :codex_rebuilder,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      aliases: aliases()
    ]
  end

  def application do
    [
      extra_applications: [:logger, :crypto],
      mod: {CodexRebuilder.Application, []}
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"},
      {:ex_json_schema, "~> 0.10"},
      {:nimble_options, "~> 1.0"},
      {:nimble_parsec, "~> 1.4"},
      {:stream_data, "~> 1.0", only: :test},
      {:castore, "~> 1.0"}
    ]
  end

  defp aliases do
    [
      "codex.rebuild": [&CodexRebuilder.CLI.run/1]
    ]
  end
end
