function stripConflictHeader(segment: string): string {
  const firstNewline = segment.indexOf("\n");
  if (firstNewline === -1) {
    return segment.trim();
  }
  const header = segment.slice(0, firstNewline);
  if (header.trim().length === 0) {
    return segment.slice(firstNewline + 1);
  }
  return segment.slice(firstNewline + 1);
}

export interface ConflictBlock {
  start: number;
  end: number;
  ours: string;
  theirs: string;
  chosen: "ours" | "theirs";
}

export interface ConflictHealResult {
  healedText: string;
  conflicts: ConflictBlock[];
}

const START_MARK = "<<<<<<<";
const MID_MARK = "=======";
const END_MARK = ">>>>>>";

export function healConflictMarkers(text: string): ConflictHealResult {
  if (!text.includes(START_MARK)) {
    return { healedText: text, conflicts: [] };
  }

  let cursor = 0;
  const conflicts: ConflictBlock[] = [];
  let output = "";

  while (cursor < text.length) {
    const start = text.indexOf(START_MARK, cursor);
    if (start === -1) {
      output += text.slice(cursor);
      break;
    }
    output += text.slice(cursor, start);

    const mid = text.indexOf(MID_MARK, start + START_MARK.length);
    const end = text.indexOf(END_MARK, mid + MID_MARK.length);
    if (mid === -1 || end === -1) {
      output += text.slice(start);
      break;
    }

    const oursRaw = text.slice(start + START_MARK.length, mid);
    const theirsRaw = text.slice(mid + MID_MARK.length, end);
    const ours = stripConflictHeader(oursRaw);
    const theirs = stripConflictHeader(theirsRaw);

    const oursTrim = ours.trim();
    const theirsTrim = theirs.trim();

    const oursScore = oursTrim.length;
    const theirsScore = theirsTrim.length;

    let chosen: "ours" | "theirs" = "ours";
    if (theirsScore > oursScore) {
      chosen = "theirs";
    } else if (theirsScore === oursScore && theirsTrim.length && !oursTrim.length) {
      chosen = "theirs";
    }

    const replacement = chosen === "ours" ? ours : theirs;
    output += replacement;

    conflicts.push({
      start,
      end: end + END_MARK.length,
      ours,
      theirs,
      chosen,
    });

    cursor = end + END_MARK.length;
  }

  return { healedText: output, conflicts };
}
