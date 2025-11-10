import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import equal from "fast-deep-equal";

const hasStructuredClone = typeof (globalThis as { structuredClone?: unknown }).structuredClone === "function";

function clone<T>(value: T): T {
  if (value === undefined || value === null) {
    return value;
  }
  if (typeof value !== "object") {
    return value;
  }
  if (hasStructuredClone) {
    return (globalThis as { structuredClone: (input: unknown) => T }).structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

export interface ConflictSegment {
  clean: string;
  a?: string;
  b?: string;
}

export function stripConflictMarkers(text: string): ConflictSegment[] {
  const segments: ConflictSegment[] = [];
  const conflictRegex = /<<<<<<<[^\n]*\n([\s\S]*?)=======\n([\s\S]*?)>>>>>>>[^\n]*\n?/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = conflictRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const preceding = text.slice(lastIndex, match.index);
      if (preceding) {
        segments.push({ clean: preceding });
      }
    }

    const a = match[1];
    const b = match[2];
    segments.push({ clean: a, a, b });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    const trailing = text.slice(lastIndex);
    if (trailing) {
      segments.push({ clean: trailing });
    }
  }

  if (segments.length === 0) {
    segments.push({ clean: text });
  }

  return segments;
}

export function chooseNewerOrLonger(
  a: string,
  b: string,
  ma?: number,
  mb?: number
): string {
  if (ma && mb && ma !== mb) {
    return mb > ma ? b : a;
  }
  if (a.length === b.length) {
    return b > a ? b : a;
  }
  return b.length >= a.length ? b : a;
}

function uniqueArray(values: any[]): any[] {
  const result: any[] = [];
  for (const value of values) {
    if (!result.some((existing) => equal(existing, value))) {
      result.push(value);
    }
  }
  return result;
}

export function deepMerge(a: any, b: any, options?: { keyPath?: (string | number)[] }): any {
  if (a === undefined) return clone(b);
  if (b === undefined) return clone(a);

  if (typeof a !== typeof b) {
    return clone(b);
  }

  if (Array.isArray(a) && Array.isArray(b)) {
    return uniqueArray([...a, ...b]);
  }

  if (a && b && typeof a === "object" && typeof b === "object") {
    const result: Record<string, any> = Array.isArray(a) ? [] : {};
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const key of keys) {
      const nextPath = options?.keyPath ? [...options.keyPath, key] : [key];
      (result as any)[key] = deepMerge(a[key], b[key], { keyPath: nextPath });
    }
    return result;
  }

  if (typeof a === "string" && typeof b === "string") {
    const key = options?.keyPath?.[options.keyPath.length - 1];
    if (key && ["definition", "origin", "story"].includes(String(key))) {
      if (a.trim() === b.trim()) {
        return a;
      }
      return `${a.trim()}\n\n— MERGED VARIANT —\n\n${b.trim()}`;
    }
    return chooseNewerOrLonger(a, b);
  }

  if (typeof a === "number" && typeof b === "number") {
    return Number.isFinite(b) ? b : a;
  }

  if (typeof a === "boolean" && typeof b === "boolean") {
    return b;
  }

  return clone(b);
}

export function cefrSortKey(level: string): number {
  const order: Record<string, number> = {
    A1: 1,
    A2: 2,
    B1: 3,
    B2: 4,
    C1: 5,
    C2: 6,
    UNSET: 7,
  };
  return order[level as keyof typeof order] ?? 7;
}

export function ensureDir(dirPath: string) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

export function resolveRoot(...segments: string[]): string {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(__dirname, "..", ...segments);
}
