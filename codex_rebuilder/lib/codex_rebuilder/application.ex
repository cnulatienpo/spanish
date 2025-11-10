defmodule CodexRebuilder.Application do
  @moduledoc false

  use Application

  @impl Application
  def start(_type, _args) do
    children = [
      {Task.Supervisor, name: CodexRebuilder.TaskSupervisor, restart: :transient}
    ]

    opts = [strategy: :one_for_one, name: CodexRebuilder.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
