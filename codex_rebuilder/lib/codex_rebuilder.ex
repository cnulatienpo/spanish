defmodule CodexRebuilder do
  @moduledoc """
  High level orchestration for rebuilding the Codex corpus.
  """

  alias CodexRebuilder.{Audit, Conflicts, FS, Merger, Normalizer, Parser, Validator}

  @concurrency 12

  @spec run(map()) :: {:ok, map()} | {:error, term()}
  def run(opts) do
    root = Map.fetch!(opts, :root)
    write? = Map.get(opts, :write, true)
    strict? = Map.get(opts, :strict, false)

    content_root = Path.join(root, "content")
    files = FS.scan(content_root)

    initial_state = %{
      lessons: [],
      vocab: [],
      rejects: [],
      conflicts: 0,
      fragments: 0
    }

    result =
      files
      |> Task.async_stream(fn file -> process_file(file) end,
        ordered: false,
        max_concurrency: @concurrency,
        timeout: :infinity,
        on_timeout: :kill_task
      )
      |> Enum.reduce(initial_state, &accumulate_results/2)

    {deduped_lessons, lesson_dups} = Merger.dedupe_lessons(result.lessons)
    {deduped_vocab, vocab_dups} = Merger.dedupe_vocab(result.vocab)

    {valid_lessons, invalid_lessons} = Validator.validate_lessons(deduped_lessons)
    {valid_vocab, invalid_vocab} = Validator.validate_vocab(deduped_vocab)

    unset_count =
      Enum.count(valid_lessons, &(&1["level"] == "UNSET")) +
        Enum.count(valid_vocab, &(&1["level"] == "UNSET"))

    rejects = result.rejects ++ invalid_lessons ++ invalid_vocab

    sorted_lessons = Merger.sort(valid_lessons)
    sorted_vocab = Merger.sort(valid_vocab)

    report = %{
      files: length(files),
      conflicts: result.conflicts,
      counts: %{lessons: length(sorted_lessons), vocab: length(sorted_vocab)},
      duplicates: lesson_dups + vocab_dups,
      unset: unset_count,
      rejects: length(rejects),
      reject_details: rejects,
      strict: strict?
    }

    audit = Audit.build(report)

    maybe_write_outputs(write?, root, sorted_lessons, sorted_vocab, rejects, audit.markdown)

    {:ok, Map.put(audit, :strict_failure, audit.strict_failure)}
  end

  defp process_file(%{path: path, rel_path: rel_path, mtime: mtime}) do
    case File.read(path) do
      {:ok, content} -> process_content(content, rel_path, mtime)
      {:error, reason} -> %{lessons: [], vocab: [], rejects: [%{reason: reason, path: rel_path}], conflicts: 0, fragments: 0}
    end
  end

  defp process_content(content, path, mtime) do
    healed = Conflicts.heal(content)

    {fragments, fragment_rejects_raw} =
      healed.segments
      |> Enum.map(&Parser.extract_json/1)
      |> Enum.reduce({[], []}, fn {ok, rejects}, {acc_ok, acc_rej} ->
        {ok ++ acc_ok, rejects ++ acc_rej}
      end)

    fragment_rejects = Enum.map(fragment_rejects_raw, &Map.put(&1, :path, path))
    conflict_rejects = Enum.map(healed.rejects, &Map.put(&1, :path, path))

    {classifications, classify_rejects} =
      fragments
      |> Enum.reduce({[], []}, fn %{data: data}, {acc, rej} ->
        {items, rejects} = Normalizer.classify_and_normalize(data, path, mtime)
        {acc ++ items, rej ++ rejects}
      end)

    lessons = for {:lesson, lesson} <- classifications, do: lesson
    vocab = for {:vocab, entry} <- classifications, do: entry

    %{
      lessons: lessons,
      vocab: vocab,
      rejects: fragment_rejects ++ classify_rejects ++ conflict_rejects,
      conflicts: healed.healed,
      fragments: length(fragments)
    }
  end

  defp accumulate_results({:ok, file_result}, acc) do
    %{
      lessons: acc.lessons ++ file_result.lessons,
      vocab: acc.vocab ++ file_result.vocab,
      rejects: acc.rejects ++ file_result.rejects,
      conflicts: acc.conflicts + file_result.conflicts,
      fragments: acc.fragments + file_result.fragments
    }
  end

  defp accumulate_results({:exit, _}, acc), do: acc

  defp maybe_write_outputs(false, _root, _lessons, _vocab, _rejects, _audit), do: :ok

  defp maybe_write_outputs(true, root, lessons, vocab, rejects, audit) do
    canonical_dir = Path.join(root, "build/canonical")
    rejects_dir = Path.join(root, "build/rejects")
    report_dir = Path.join(root, "build/reports")

    Enum.each([canonical_dir, rejects_dir, report_dir], &File.mkdir_p!/1)

    lessons_json = encode_pretty(lessons)
    vocab_json = encode_pretty(vocab)

    File.write!(Path.join(canonical_dir, "lessons.mmspanish.json"), lessons_json)
    File.write!(Path.join(canonical_dir, "vocabulary.mmspanish.json"), vocab_json)

    rejects
    |> Enum.with_index()
    |> Enum.each(fn {reject, idx} ->
      name = Path.join(rejects_dir, "reject_#{idx + 1}.json")
      File.write!(name, Jason.encode_to_iodata!(canonicalize(reject)))
    end)

    File.write!(Path.join(report_dir, "audit.md"), audit)

    ensure_idempotent?(canonical_dir)
  end

  defp encode_pretty(data) do
    data
    |> canonicalize()
    |> Jason.encode!(pretty: true)
  end

  defp canonicalize(list) when is_list(list), do: Enum.map(list, &canonicalize/1)
  defp canonicalize(%{} = map) do
    map
    |> Enum.map(fn {k, v} -> {k, canonicalize(v)} end)
    |> Enum.sort_by(fn {k, _} -> k end)
    |> Map.new()
  end
  defp canonicalize(other), do: other

  defp ensure_idempotent?(canonical_dir) do
    lessons_path = Path.join(canonical_dir, "lessons.mmspanish.json")
    vocab_path = Path.join(canonical_dir, "vocabulary.mmspanish.json")
    hash = fn path -> :crypto.hash(:sha256, File.read!(path)) end

    original = {hash.(lessons_path), hash.(vocab_path)}
    rehash = {hash.(lessons_path), hash.(vocab_path)}

    if original != rehash do
      raise "idempotency check failed"
    end
  end
end
