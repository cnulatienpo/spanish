import { ensureDir } from "https://deno.land/std@0.224.0/fs/ensure_dir.ts";
import { join, relative, dirname } from "https://deno.land/std@0.224.0/path/mod.ts";

export interface ContentFileInfo {
  path: string;
  mtimeMs: number;
  text: string;
}

export interface ContentFileMeta {
  path: string;
  mtimeMs: number;
}

export async function gatherContentFiles(root: string): Promise<ContentFileMeta[]> {
  const results: ContentFileMeta[] = [];
  async function walk(dir: string) {
    for await (const entry of Deno.readDir(dir)) {
      const full = join(dir, entry.name);
      if (entry.isDirectory) {
        await walk(full);
      } else if (entry.isFile) {
        const stat = await Deno.stat(full);
        results.push({ path: full, mtimeMs: stat.mtime?.getTime() ?? 0 });
      }
    }
  }
  await walk(root);
  results.sort((a, b) => a.path.localeCompare(b.path));
  return results;
}

export async function readContentFile(meta: ContentFileMeta): Promise<ContentFileInfo> {
  const text = await Deno.readTextFile(meta.path);
  return { ...meta, text };
}

export function stableSortKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => stableSortKeys(item));
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    entries.sort(([a], [b]) => a.localeCompare(b));
    const sorted: Record<string, unknown> = {};
    for (const [key, val] of entries) {
      sorted[key] = stableSortKeys(val);
    }
    return sorted;
  }
  return value;
}

export function stableStringify(value: unknown): string {
  return JSON.stringify(stableSortKeys(value), null, 2) + "\n";
}

export async function writeJsonFile(filePath: string, value: unknown): Promise<void> {
  await ensureDir(dirname(filePath));
  await Deno.writeTextFile(filePath, stableStringify(value));
}

export async function writeTextFile(filePath: string, value: string): Promise<void> {
  await ensureDir(dirname(filePath));
  await Deno.writeTextFile(filePath, value);
}

export async function digestHex(data: string, algorithm: "BLAKE2B-256" | "SHA-256" = "BLAKE2B-256"): Promise<string> {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(data);
  let buffer: ArrayBuffer;
  try {
    buffer = await crypto.subtle.digest(algorithm, bytes);
  } catch (err) {
    if (algorithm === "BLAKE2B-256") {
      buffer = await crypto.subtle.digest("SHA-256", bytes);
    } else {
      throw err;
    }
  }
  const slice = new Uint8Array(buffer).slice(0, 16);
  return Array.from(slice).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function toRelative(path: string, root: string): string {
  return relative(root, path) || ".";
}

export interface AuditRecord {
  filesScanned: number;
  conflictsHealed: number;
  fragmentsParsed: number;
  lessonsTotal: number;
  vocabularyTotal: number;
  duplicateClusters: number;
  unsetLevelIds: string[];
  rejects: { file: string; reason: string }[];
  runDurationMs: number;
}

export function formatAuditMarkdown(audit: AuditRecord): string {
  const lines: string[] = [];
  lines.push(`# Codex Rebuild Audit`);
  lines.push("");
  lines.push(`* Files scanned: **${audit.filesScanned}**`);
  lines.push(`* Conflict blocks healed: **${audit.conflictsHealed}**`);
  lines.push(`* Fragments parsed: **${audit.fragmentsParsed}**`);
  lines.push(`* Lessons emitted: **${audit.lessonsTotal}**`);
  lines.push(`* Vocabulary emitted: **${audit.vocabularyTotal}**`);
  lines.push(`* Duplicate clusters merged: **${audit.duplicateClusters}**`);
  lines.push(`* Items with level=UNSET: **${audit.unsetLevelIds.length}**`);
  if (audit.unsetLevelIds.length) {
    lines.push("");
    lines.push("## Items with UNSET level");
    for (const id of audit.unsetLevelIds) {
      lines.push(`- ${id}`);
    }
  }
  if (audit.rejects.length) {
    lines.push("");
    lines.push("## Rejects");
    for (const reject of audit.rejects) {
      lines.push(`- ${reject.file}: ${reject.reason}`);
    }
  }
  lines.push("");
  lines.push(`Run duration: ${(audit.runDurationMs / 1000).toFixed(2)}s`);
  lines.push("");
  return lines.join("\n");
}

export async function writeAuditMarkdown(path: string, audit: AuditRecord): Promise<void> {
  await writeTextFile(path, formatAuditMarkdown(audit));
}

export interface RejectRecord {
  file: string;
  reason: string;
  content: string;
}

export async function writeRejectFragments(dir: string, rejects: RejectRecord[]): Promise<void> {
  await ensureDir(dir);
  let counter = 0;
  for (const reject of rejects) {
    counter += 1;
    const filePath = join(dir, `${counter.toString().padStart(4, "0")}_${sanitizeFileName(reject.file)}.txt`);
    const body = [`# Source: ${reject.file}`, `# Reason: ${reject.reason}`, "", reject.content].join("\n");
    await Deno.writeTextFile(filePath, body);
  }
}

function sanitizeFileName(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

export function unionStringArrays(primary: string[], additional: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of [...primary, ...additional]) {
    const key = value.trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result;
}

export function now(): number {
  return Date.now();
}
