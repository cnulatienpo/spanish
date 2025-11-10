defmodule CodexRebuilder.Audit do
  @moduledoc """
  Builds human readable and structured audit data from the pipeline run.
  """

  def build(report) do
    console = console_summary(report)
    markdown = markdown_report(report)
    %{console: console, markdown: markdown, strict_failure: strict?(report)}
  end

  defp console_summary(%{files: files, conflicts: conflicts, counts: counts, duplicates: duplicates, unset: unset, rejects: rejects}) do
    [
      "🔍 Scanned #{files} files",
      "⚔️  Healed #{conflicts} conflict blocks",
      "📚  #{counts.vocab} vocab | #{counts.lessons} lessons",
      "✅  #{duplicates} duplicate clusters merged",
      (if unset > 0, do: "⚠️  #{unset} items with UNSET level", else: ""),
      (if rejects > 0, do: "🚫  #{rejects} rejects saved", else: "")
    ]
    |> Enum.reject(&(&1 == ""))
    |> Enum.join("\n")
  end

  defp markdown_report(report) do
    [
      "# Codex Rebuild Audit",
      "",
      "* Files scanned: #{report.files}",
      "* Conflicts healed: #{report.conflicts}",
      "* Vocabulary entries: #{report.counts.vocab}",
      "* Lesson entries: #{report.counts.lessons}",
      "* Duplicate clusters merged: #{report.duplicates}",
      "* Items with UNSET level: #{report.unset}",
      "* Rejects: #{report.rejects}",
      "",
      "## Reject Summary",
      build_reject_section(report.reject_details)
    ]
    |> Enum.join("\n")
  end

  defp build_reject_section([]), do: "(none)"

  defp build_reject_section(rejects) do
    rejects
    |> Enum.map(fn reject ->
      "- #{reject.reason}: #{reject.path || reject[:type]}"
    end)
    |> Enum.join("\n")
  end

  defp strict?(%{strict: true, rejects: rejects, unset: unset}) do
    rejects > 0 or unset > 0
  end

  defp strict?(_), do: false
end
