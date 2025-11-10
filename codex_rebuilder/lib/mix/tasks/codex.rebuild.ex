defmodule Mix.Tasks.Codex.Rebuild do
  @moduledoc "Runs the codex rebuilder pipeline."
  use Mix.Task

  @shortdoc "Rebuild the MixMethod Spanish codex"

  @impl Mix.Task
  def run(args) do
    CodexRebuilder.CLI.run(args)
  end
end
