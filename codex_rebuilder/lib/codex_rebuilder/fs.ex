defmodule CodexRebuilder.FS do
  @moduledoc """
  Filesystem helpers for scanning the `content/` tree and gathering metadata.
  """

  @doc """
  Returns a list of file descriptors under the given `root` directory.

  Each descriptor is `%{path: abs_path, rel_path: rel_path, mtime: mtime}`.
  Files that cannot be stat'ed are skipped.
  """
  def scan(root) do
    root = Path.expand(root)

    if File.dir?(root) do
      do_scan(root)
    else
      []
    end
  end

  defp do_scan(root) do
    root
    |> Path.join("**/*")
    |> Path.wildcard(match_dot: true)
    |> Enum.filter(&File.regular?/1)
    |> Enum.map(&descriptor(&1, root))
    |> Enum.reject(&is_nil/1)
  end

  defp descriptor(path, root) do
    rel_path = Path.relative_to(path, Path.dirname(root))

    case File.stat(path, time: :posix) do
      {:ok, %File.Stat{mtime: mtime}} -> %{path: path, rel_path: rel_path, mtime: mtime}
      {:error, _} -> nil
    end
  end
end
