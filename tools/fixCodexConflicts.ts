import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import chalk from "chalk";
import { globby } from "globby";
import JSON5 from "json5";
import slugify from "slugify";

import {
  stripConflictMarkers,
  deepMerge,
  ensureDir,
  resolveRoot,
  cefrSortKey,
} from "./utils.js";
import {
  Lesson,
  Vocabulary,
  validateLesson,
  validateVocabulary,
  CEFRLevel,
} from "./models.js";

interface RejectRecord {
  path: string;
  reason: string;
  snippet: string;
}

interface ParsedVariant {
  success: boolean;
  entries: any[];
  error?: Error;
}

const args = process.argv.slice(2);
const checkMode = args.includes("--check");
const strictMode = args.includes("--strict");

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const contentDir = path.join(rootDir, "content");

if (!fs.existsSync(contentDir)) {
  console.error(chalk.red(`Missing content directory at ${contentDir}`));
  process.exit(1);
}

const stats = {
  files: 0,
  conflicts: 0,
  mergedEntries: 0,
  duplicateMerges: 0,
  rejects: 0,
  unsetLevels: 0,
};

const lessonMap = new Map<string, Lesson>();
const vocabMap = new Map<string, Vocabulary>();
const rejects: RejectRecord[] = [];

function parseVariant(text: string): ParsedVariant {
  const trimmed = text.trim();
  if (!trimmed) {
    return { success: true, entries: [] };
  }

  try {
    const parsed = JSON5.parse(trimmed);
    if (Array.isArray(parsed)) {
      return { success: true, entries: parsed };
    }
    if (parsed && typeof parsed === "object") {
      return { success: true, entries: [parsed] };
    }
    return {
      success: false,
      entries: [],
      error: new Error("Parsed value is not an object or array"),
    };
  } catch (error) {
    return { success: false, entries: [], error: error as Error };
  }
}

function keyForEntry(entry: any, index: number): string {
  if (entry && typeof entry === "object") {
    if (typeof entry.id === "string") return `id:${entry.id}`;
    if (typeof entry.spanish === "string") return `spanish:${entry.spanish.toLowerCase()}`;
    if (typeof entry.title === "string") return `title:${entry.title.toLowerCase()}`;
    if (typeof entry.nickname === "string") return `nick:${entry.nickname.toLowerCase()}`;
  }
  return `index:${index}`;
}

function normalizeTags(value: any): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return [...new Set(value.filter((item) => typeof item === "string"))];
  }
  if (typeof value === "string") {
    return [value];
  }
  return [];
}

function inferLevelFromPath(filePath: string, fallback?: string): CEFRLevel {
  const levelRegex = /(?:^|_|\b)([ABC][12])(?:\b|_|-)/i;
  const filename = path.basename(filePath);
  const match = filePath.match(levelRegex) || filename.match(levelRegex);
  if (match) {
    return match[1].toUpperCase() as CEFRLevel;
  }
  if (fallback) {
    const fallbackMatch = fallback.match(levelRegex);
    if (fallbackMatch) {
      return fallbackMatch[1].toUpperCase() as CEFRLevel;
    }
  }
  return "UNSET";
}

const LEVELS: CEFRLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2", "UNSET"];

function sanitizeLevel(level: string | undefined, filePath: string, fallback?: string): CEFRLevel {
  const upper = level ? level.toUpperCase() : undefined;
  if (upper && LEVELS.includes(upper as CEFRLevel)) {
    return upper as CEFRLevel;
  }
  const inferred = inferLevelFromPath(filePath, fallback);
  if (LEVELS.includes(inferred)) {
    return inferred;
  }
  return "UNSET";
}

function ensureSourceFiles(list: any, filePath: string): string[] {
  const arr: string[] = Array.isArray(list)
    ? list.filter((item) => typeof item === "string" && item.length > 0)
    : [];
  if (filePath && !arr.includes(filePath)) {
    arr.push(filePath);
  }
  return [...new Set(arr)].sort();
}

function mergeSourceFiles(...lists: string[][]): string[] {
  const combined = lists.flat().filter((item) => typeof item === "string" && item.length > 0);
  return [...new Set(combined)].sort();
}

function normalizeLesson(entry: any, filePath: string): Lesson {
  if (!entry || typeof entry !== "object") {
    throw new Error("Lesson entry is not an object");
  }

  const title = typeof entry.title === "string" ? entry.title : undefined;
  const nicknameRaw = typeof entry.nickname === "string" ? entry.nickname : undefined;
  const unitValue = typeof entry.unit === "number" ? entry.unit : parseInt(entry.unit, 10);
  const lessonNumberValue =
    typeof entry.lesson_number === "number"
      ? entry.lesson_number
      : parseInt(entry.lesson_number, 10);

  if (!title) {
    throw new Error("Lesson missing title");
  }

  const nickname = nicknameRaw || slugify(title, { lower: true, strict: true });

  const id = typeof entry.id === "string" && entry.id.length > 0
    ? entry.id
    : `mmspanish__grammar_${Number.isFinite(unitValue) ? unitValue : 0}_${slugify(title, {
        lower: true,
        strict: true,
      })}`;

  const level = sanitizeLevel(typeof entry.level === "string" ? entry.level : undefined, filePath, title);

  const stepsArray = Array.isArray(entry.steps) ? entry.steps : [];
  if (stepsArray.length === 0) {
    throw new Error("Lesson has no steps");
  }

  const steps = stepsArray.map((step: any) => {
    if (!step || typeof step !== "object") return step;
    const normalized: any = { ...step };
    if (typeof normalized.phase !== "string") {
      throw new Error("Lesson step missing phase");
    }
    if (typeof step.items === "string") {
      normalized.items = [step.items];
    }
    if (Array.isArray(step.items)) {
      normalized.items = step.items.filter((item: any) => typeof item === "string");
    }
    return normalized;
  });

  const tags = normalizeTags(entry.tags);

  const notes = typeof entry.notes === "string" && entry.notes.trim().length > 0 ? entry.notes : undefined;

  return {
    id,
    title,
    nickname,
    level: level as CEFRLevel,
    unit: Number.isFinite(unitValue) ? unitValue : 0,
    lesson_number: Number.isFinite(lessonNumberValue) ? lessonNumberValue : 0,
    tags,
    steps,
    notes,
    source_files: ensureSourceFiles(entry.source_files, filePath),
  };
}

function normalizeExamples(value: any): { es: string; en: string }[] {
  if (!value) return [];
  const arr = Array.isArray(value) ? value : [value];
  const normalized = arr
    .map((example) => {
      if (!example || typeof example !== "object") return null;
      const es = typeof example.es === "string" ? example.es : undefined;
      const en = typeof example.en === "string" ? example.en : undefined;
      if (!es || !en) return null;
      return { es, en };
    })
    .filter((item): item is { es: string; en: string } => Boolean(item));
  const seen = new Set<string>();
  const deduped: { es: string; en: string }[] = [];
  for (const item of normalized) {
    const key = `${item.es}||${item.en}`;
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(item);
    }
  }
  return deduped;
}

function normalizeVocabulary(entry: any, filePath: string): Vocabulary {
  if (!entry || typeof entry !== "object") {
    throw new Error("Vocabulary entry is not an object");
  }

  const spanish = typeof entry.spanish === "string" ? entry.spanish : undefined;
  const pos = typeof entry.pos === "string" ? entry.pos : undefined;
  const english = typeof entry.english_gloss === "string" ? entry.english_gloss : undefined;
  const definition = typeof entry.definition === "string" ? entry.definition : undefined;

  if (!spanish || !pos || !english || !definition) {
    throw new Error("Vocabulary missing required fields");
  }

  const id = typeof entry.id === "string" && entry.id.length > 0
    ? entry.id
    : `mmspanish__vocab_${slugify(spanish, { lower: true, strict: true })}`;

  const level = sanitizeLevel(typeof entry.level === "string" ? entry.level : undefined, filePath, spanish);

  const tags = normalizeTags(entry.tags);
  const examples = normalizeExamples(entry.examples);

  const origin = typeof entry.origin === "string" ? entry.origin : undefined;
  const story = typeof entry.story === "string" ? entry.story : undefined;
  const notes = typeof entry.notes === "string" && entry.notes.trim().length > 0 ? entry.notes : undefined;

  const gender =
    typeof entry.gender === "string"
      ? (entry.gender === "masculine" || entry.gender === "feminine"
          ? entry.gender
          : null)
      : entry.gender === null
      ? null
      : undefined;

  return {
    id,
    spanish,
    pos: pos as Vocabulary["pos"],
    gender,
    english_gloss: english,
    definition,
    origin,
    story,
    examples,
    level: level as CEFRLevel,
    tags,
    source_files: ensureSourceFiles(entry.source_files, filePath),
    notes,
  };
}

function classifyEntry(entry: any): ("lesson" | "vocabulary")[] {
  if (!entry || typeof entry !== "object") return [];
  const lessonSignals = Boolean(entry.steps || entry.nickname || entry.lesson_number);
  const vocabSignals = Boolean(entry.spanish || entry.definition || entry.pos);
  if (lessonSignals && vocabSignals) return ["lesson", "vocabulary"];
  if (lessonSignals) return ["lesson"];
  if (vocabSignals) return ["vocabulary"];
  return [];
}

function addLesson(lesson: Lesson) {
  const existing = lessonMap.get(lesson.id);
  if (existing) {
    const merged = deepMerge(existing, lesson, { keyPath: [] }) as Lesson;
    merged.source_files = mergeSourceFiles(existing.source_files, lesson.source_files);
    merged.tags = [...new Set(merged.tags)];
    lessonMap.set(lesson.id, merged);
    stats.duplicateMerges += 1;
  } else {
    lessonMap.set(lesson.id, lesson);
  }
}

function addVocabulary(vocab: Vocabulary) {
  const existing = vocabMap.get(vocab.id);
  if (existing) {
    const merged = deepMerge(existing, vocab, { keyPath: [] }) as Vocabulary;
    merged.source_files = mergeSourceFiles(existing.source_files, vocab.source_files);
    merged.tags = [...new Set(merged.tags)];
    vocabMap.set(vocab.id, merged);
    stats.duplicateMerges += 1;
  } else {
    vocabMap.set(vocab.id, vocab);
  }
}

function processEntry(entry: any, filePath: string) {
  const kinds = classifyEntry(entry);
  if (kinds.length === 0) {
    rejects.push({
      path: filePath,
      reason: "Unclassified entry",
      snippet: JSON.stringify(entry, null, 2),
    });
    return;
  }

  for (const kind of kinds) {
    try {
      if (kind === "lesson") {
        const lesson = normalizeLesson(entry, filePath);
        addLesson(lesson);
      } else if (kind === "vocabulary") {
        const vocab = normalizeVocabulary(entry, filePath);
        addVocabulary(vocab);
      }
      stats.mergedEntries += 1;
    } catch (error) {
      rejects.push({
        path: filePath,
        reason: `${kind} normalization failed: ${(error as Error).message}`,
        snippet: JSON.stringify(entry, null, 2),
      });
    }
  }
}

async function main() {
  const files = await globby(["content/**/*"], { cwd: rootDir, onlyFiles: true });
  stats.files = files.length;

  const scanningLine = `🔍 Scanning ${files.length.toLocaleString()} files...`;
  console.log(chalk.cyan(scanningLine));

  for (const relativePath of files) {
    const filePath = path.join(rootDir, relativePath);
    const raw = fs.readFileSync(filePath, "utf8");
    const segments = stripConflictMarkers(raw);
    const conflictBlocks = segments.filter((segment) => segment.a !== undefined && segment.b !== undefined).length;
    stats.conflicts += conflictBlocks;

    const variantA = segments.map((segment) => (segment.a ?? segment.clean)).join("");
    const variantB = segments.map((segment) => (segment.b ?? segment.clean)).join("");

    const parsedA = parseVariant(variantA);
    const parsedB = parseVariant(variantB);

    if (!parsedA.success && !parsedB.success) {
      rejects.push({
        path: relativePath,
        reason: "Failed to parse conflict variants",
        snippet: raw.slice(0, 2000),
      });
      continue;
    }

    const entriesA = parsedA.success ? parsedA.entries : [];
    const entriesB = parsedB.success ? parsedB.entries : [];
    const map = new Map<string, any>();

    entriesA.forEach((entry, index) => {
      const key = keyForEntry(entry, index);
      map.set(key, entry);
    });

    entriesB.forEach((entry, index) => {
      const key = keyForEntry(entry, index);
      if (map.has(key)) {
        const merged = deepMerge(map.get(key), entry, { keyPath: [] });
        map.set(key, merged);
      } else {
        map.set(key, entry);
      }
    });

    const finalEntries = Array.from(map.values());

    if (finalEntries.length === 0 && (parsedA.success || parsedB.success)) {
      rejects.push({
        path: relativePath,
        reason: "No entries extracted",
        snippet: raw.slice(0, 1000),
      });
      continue;
    }

    for (const entry of finalEntries) {
      processEntry(entry, relativePath);
    }
  }

  const lessons = Array.from(lessonMap.values()).map((lesson) => ({
    ...lesson,
    source_files: [...new Set(lesson.source_files)].sort(),
    tags: [...new Set(lesson.tags)].sort(),
  }));
  const vocabulary = Array.from(vocabMap.values()).map((vocab) => ({
    ...vocab,
    source_files: [...new Set(vocab.source_files)].sort(),
    tags: [...new Set(vocab.tags)].sort(),
    examples: vocab.examples,
  }));

  lessons.sort((a, b) => {
    const levelDiff = cefrSortKey(a.level) - cefrSortKey(b.level);
    if (levelDiff !== 0) return levelDiff;
    const unitDiff = (a.unit ?? 0) - (b.unit ?? 0);
    if (unitDiff !== 0) return unitDiff;
    const lessonDiff = (a.lesson_number ?? 0) - (b.lesson_number ?? 0);
    if (lessonDiff !== 0) return lessonDiff;
    return a.id.localeCompare(b.id);
  });

  vocabulary.sort((a, b) => {
    const levelDiff = cefrSortKey(a.level) - cefrSortKey(b.level);
    if (levelDiff !== 0) return levelDiff;
    return a.id.localeCompare(b.id);
  });

  const invalidLessons: { item: Lesson; errors: string }[] = [];
  const invalidVocabulary: { item: Vocabulary; errors: string }[] = [];

  for (const lesson of lessons) {
    if (!validateLesson(lesson)) {
      invalidLessons.push({ item: lesson, errors: JSON.stringify(validateLesson.errors, null, 2) });
    }
    if (lesson.level === "UNSET") {
      stats.unsetLevels += 1;
    }
  }

  for (const vocab of vocabulary) {
    if (!validateVocabulary(vocab)) {
      invalidVocabulary.push({ item: vocab, errors: JSON.stringify(validateVocabulary.errors, null, 2) });
    }
    if (vocab.level === "UNSET") {
      stats.unsetLevels += 1;
    }
  }

  for (const invalid of invalidLessons) {
    rejects.push({
      path: invalid.item.id,
      reason: "Lesson schema validation failed",
      snippet: invalid.errors,
    });
  }

  for (const invalid of invalidVocabulary) {
    rejects.push({
      path: invalid.item.id,
      reason: "Vocabulary schema validation failed",
      snippet: invalid.errors,
    });
  }

  stats.rejects = rejects.length;

  const reportLines = [
    scanningLine,
    `⚔️  ${stats.conflicts.toLocaleString()} conflict blocks repaired`,
    `📚  ${vocabulary.length.toLocaleString()} vocab entries | ${lessons.length.toLocaleString()} lessons`,
    `✅  ${stats.duplicateMerges.toLocaleString()} duplicates merged`,
    `⚠️  ${stats.unsetLevels.toLocaleString()} items with UNSET level`,
    `🚫  ${stats.rejects.toLocaleString()} rejects saved`,
  ];

  reportLines.slice(1).forEach((line) => {
    if (line.startsWith("⚠️")) {
      console.log(chalk.yellow(line));
    } else if (line.startsWith("🚫")) {
      console.log(chalk.red(line));
    } else if (line.startsWith("⚔️")) {
      console.log(chalk.magenta(line));
    } else if (line.startsWith("✅")) {
      console.log(chalk.green(line));
    } else if (line.startsWith("📚")) {
      console.log(chalk.blue(line));
    } else {
      console.log(line);
    }
  });

  if (!checkMode) {
    const canonicalDir = resolveRoot("build", "canonical");
    const reportDir = resolveRoot("build", "reports");
    const rejectsDir = resolveRoot("build", "rejects");
    if (fs.existsSync(rejectsDir)) {
      fs.rmSync(rejectsDir, { recursive: true, force: true });
    }
    ensureDir(canonicalDir);
    ensureDir(reportDir);
    ensureDir(rejectsDir);

    fs.writeFileSync(
      path.join(canonicalDir, "lessons.mmspanish.json"),
      JSON.stringify(lessons, null, 2),
      "utf8"
    );
    fs.writeFileSync(
      path.join(canonicalDir, "vocabulary.mmspanish.json"),
      JSON.stringify(vocabulary, null, 2),
      "utf8"
    );

    const auditPath = path.join(reportDir, "audit.md");
    fs.writeFileSync(auditPath, reportLines.join("\n") + "\n", "utf8");

    rejects.forEach((reject, index) => {
      const fileName = `reject_${String(index + 1).padStart(4, "0")}.json`;
      const payload = {
        path: reject.path,
        reason: reject.reason,
        snippet: reject.snippet,
      };
      fs.writeFileSync(path.join(rejectsDir, fileName), JSON.stringify(payload, null, 2), "utf8");
    });
  }

  if (strictMode) {
    if (
      invalidLessons.length > 0 ||
      invalidVocabulary.length > 0 ||
      stats.unsetLevels > 0 ||
      rejects.length > 0
    ) {
      console.error(chalk.red("Strict mode: invalid data detected"));
      process.exit(1);
    }
  }

  console.log(chalk.cyan("✨ Done. Canonical JSONs written to build/canonical/"));
}

main().catch((error) => {
  console.error(chalk.red(error instanceof Error ? error.stack : String(error)));
  process.exit(1);
});
