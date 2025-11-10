// deno-lint-ignore-file no-explicit-any
import { parse } from "https://deno.land/std@0.224.0/flags/mod.ts";
import { dirname, fromFileUrl, join } from "https://deno.land/std@0.224.0/path/mod.ts";

import { gatherContentFiles, readContentFile, writeJsonFile, writeRejectFragments, writeAuditMarkdown, stableStringify, now, AuditRecord, toRelative, RejectRecord } from "./io.ts";
import { normalizeContentFile, cefrSorter, NormalizedLesson, NormalizedVocabulary } from "./normalize.ts";
import { mergeNormalized } from "./merge.ts";
import { assertLesson, assertVocabulary, Lesson, Vocabulary } from "./models.ts";

interface PipelineOptions {
  repoRoot: string;
  contentRoot: string;
}

interface PipelineOutput {
  lessons: Lesson[];
  vocabulary: Vocabulary[];
  rejects: RejectRecord[];
  conflictsHealed: number;
  fragmentsParsed: number;
  duplicateClusters: number;
  filesScanned: number;
  unsetLevelIds: string[];
}

async function executePipeline(options: PipelineOptions): Promise<PipelineOutput> {
  const files = await gatherContentFiles(options.contentRoot);
  const lessonsNormalized: NormalizedLesson[] = [];
  const vocabularyNormalized: NormalizedVocabulary[] = [];
  const rejects = [] as PipelineOutput["rejects"];
  let conflictsHealed = 0;
  let fragmentsParsed = 0;

  for (const meta of files) {
    const info = await readContentFile(meta);
    const relativePath = toRelative(info.path, options.repoRoot);
    const result = await normalizeContentFile(info, relativePath);
    lessonsNormalized.push(...result.lessons);
    vocabularyNormalized.push(...result.vocabulary);
    rejects.push(...result.rejects);
    conflictsHealed += result.conflicts;
    fragmentsParsed += result.fragments;
  }

  const merged = mergeNormalized(lessonsNormalized, vocabularyNormalized);
  const lessons = merged.mergedLessons.map((entry) => entry.data);
  const vocabulary = merged.mergedVocabulary.map((entry) => entry.data);

  const lessonsSorted = [...lessons].sort(cefrSorter);
  const vocabularySorted = [...vocabulary].sort((a, b) => {
    const levelA = levelOrder(a.level);
    const levelB = levelOrder(b.level);
    if (levelA !== levelB) return levelA - levelB;
    return a.id.localeCompare(b.id);
  });

  const unsetLevelIds = [
    ...lessonsSorted.filter((item) => item.level === "UNSET").map((item) => item.id),
    ...vocabularySorted.filter((item) => item.level === "UNSET").map((item) => item.id),
  ];

  const lessonErrors = validateLessons(lessonsSorted);
  const vocabErrors = validateVocabulary(vocabularySorted);
  if (lessonErrors.length || vocabErrors.length) {
    const message = [...lessonErrors, ...vocabErrors].join("\n");
    throw new Error(`Schema validation failed:\n${message}`);
  }

  return {
    lessons: lessonsSorted,
    vocabulary: vocabularySorted,
    rejects,
    conflictsHealed,
    fragmentsParsed,
    duplicateClusters: merged.duplicateClusters,
    filesScanned: files.length,
    unsetLevelIds,
  };
}

function validateLessons(lessons: any[]): string[] {
  const errors: string[] = [];
  for (const lesson of lessons) {
    try {
      assertLesson(lesson);
    } catch (error) {
      errors.push(`Lesson ${lesson.id}: ${(error as Error).message}`);
    }
  }
  return errors;
}

function validateVocabulary(vocabulary: any[]): string[] {
  const errors: string[] = [];
  for (const vocab of vocabulary) {
    try {
      assertVocabulary(vocab);
    } catch (error) {
      errors.push(`Vocabulary ${vocab.id}: ${(error as Error).message}`);
    }
  }
  return errors;
}

function levelOrder(level: string): number {
  switch (level) {
    case "A1":
      return 1;
    case "A2":
      return 2;
    case "B1":
      return 3;
    case "B2":
      return 4;
    case "C1":
      return 5;
    case "C2":
      return 6;
    default:
      return 7;
  }
}

async function main() {
  const flags = parse(Deno.args, {
    boolean: ["write", "check", "strict"],
    default: { write: false, check: false, strict: false },
  });

  const mode = flags.check ? "check" : "write";
  const strict = Boolean(flags.strict);
  const toolDir = dirname(fromFileUrl(import.meta.url));
  const repoRoot = dirname(toolDir);
  const contentRoot = join(repoRoot, "content");
  const buildRoot = join(repoRoot, "build");
  const canonicalDir = join(buildRoot, "canonical");
  const reportsDir = join(buildRoot, "reports");
  const rejectsDir = join(buildRoot, "rejects");

  const start = now();
  const firstPass = await executePipeline({ repoRoot, contentRoot });
  const duration = now() - start;

  if (mode === "write") {
    const secondPass = await executePipeline({ repoRoot, contentRoot });
    const firstLessonsJson = stableStringify(firstPass.lessons);
    const firstVocabJson = stableStringify(firstPass.vocabulary);
    const secondLessonsJson = stableStringify(secondPass.lessons);
    const secondVocabJson = stableStringify(secondPass.vocabulary);
    if (firstLessonsJson !== secondLessonsJson || firstVocabJson !== secondVocabJson) {
      throw new Error("Idempotency check failed: second pass results differ");
    }

    try {
      await Deno.remove(rejectsDir, { recursive: true });
    } catch (error) {
      if (!(error instanceof Deno.errors.NotFound)) {
        throw error;
      }
    }

    await writeJsonFile(join(canonicalDir, "lessons.mmspanish.json"), firstPass.lessons);
    await writeJsonFile(join(canonicalDir, "vocabulary.mmspanish.json"), firstPass.vocabulary);
    await writeAudit(firstPass, duration, join(reportsDir, "audit.md"));
    await writeRejectFragments(rejectsDir, firstPass.rejects);
  } else {
    await writeAudit(firstPass, duration, join(reportsDir, "audit.md"));
  }

  printSummary(firstPass, duration, mode);

  if (strict) {
    if (firstPass.rejects.length > 0 || firstPass.unsetLevelIds.length > 0) {
      Deno.exit(1);
    }
  }
}

async function writeAudit(output: PipelineOutput, duration: number, target: string) {
  const audit: AuditRecord = {
    filesScanned: output.filesScanned,
    conflictsHealed: output.conflictsHealed,
    fragmentsParsed: output.fragmentsParsed,
    lessonsTotal: output.lessons.length,
    vocabularyTotal: output.vocabulary.length,
    duplicateClusters: output.duplicateClusters,
    unsetLevelIds: output.unsetLevelIds,
    rejects: output.rejects.map((reject) => ({ file: reject.file, reason: reject.reason })),
    runDurationMs: duration,
  };
  await writeAuditMarkdown(target, audit);
}

function printSummary(output: PipelineOutput, duration: number, mode: "write" | "check") {
  console.log(`🔍 Scanned ${output.filesScanned} files`);
  console.log(`⚔️  Healed ${output.conflictsHealed} conflict blocks`);
  console.log(`📚  ${output.vocabulary.length} vocab | ${output.lessons.length} lessons`);
  console.log(`✅  ${output.duplicateClusters} duplicate clusters merged`);
  console.log(`⚠️  ${output.unsetLevelIds.length} items with UNSET level`);
  console.log(`🚫  ${output.rejects.length} rejects saved`);
  console.log(`⏱️  ${(duration / 1000).toFixed(2)}s elapsed`);
  if (mode === "write") {
    console.log("✨ Canonical JSONs written to build/canonical/");
  }
}

if (import.meta.main) {
  await main();
}
