// ── Structural insertion-point helpers ─────────────────────────────────────
// Given a source string, return `{ line, column }` zero-indexed where new code
// should be inserted. All helpers return `null` when the anchor is missing;
// callers should fall back to appending at EOF and warning the user.

/**
 * Insert just after the last `import '...';` line, or at line 0 if none.
 */
export function findImportInsertionPoint(source) {
  const lines = source.split("\n");
  let lastImport = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*import\s+['"][^'"]+['"]\s*;/.test(lines[i])) {
      lastImport = i;
    }
  }
  return { line: lastImport + 1, column: 0 };
}

/**
 * Insert just before the closing `}` of the top-level block of `kind`
 * (`"Primitive"`, `"Scheme"`, or `"Game"`) with the given name. Returns the
 * line number of the closing brace. When `name` is null, matches the first
 * block of that kind.
 */
export function findBlockClosingLine(source, kind, name) {
  const lines = source.split("\n");
  const header = name
    ? new RegExp(`^\\s*${kind}\\s+${escapeRegExp(name)}\\s*\\(`)
    : new RegExp(`^\\s*${kind}\\s+\\w+\\s*\\(`);
  let inBlock = false;
  let depth = 0;
  for (let i = 0; i < lines.length; i++) {
    if (!inBlock && header.test(lines[i])) {
      inBlock = true;
      depth = 0;
    }
    if (inBlock) {
      for (const ch of lines[i]) {
        if (ch === "{") depth++;
        else if (ch === "}") {
          depth--;
          if (depth === 0) return i;
        }
      }
    }
  }
  return null;
}

/**
 * Find the line number containing the given top-level keyword (`proof:`,
 * `assume:`, `lemma:`, `theorem:`, `games:`, `let:`). Returns -1 if absent.
 */
export function findSectionLine(source, keyword) {
  const lines = source.split("\n");
  const re = new RegExp(`^\\s*${escapeRegExp(keyword)}\\s*$`);
  for (let i = 0; i < lines.length; i++) {
    if (re.test(lines[i])) return i;
  }
  return -1;
}

/**
 * Return the last line that is a member of the given section, i.e. the last
 * non-blank line between `section` and the next top-level keyword.
 */
export function findSectionLastMemberLine(source, section) {
  const start = findSectionLine(source, section);
  if (start === -1) return -1;
  const lines = source.split("\n");
  const nextKeyword = /^\s*(let|assume|lemma|theorem|games|proof):\s*$/;
  let last = start;
  for (let i = start + 1; i < lines.length; i++) {
    if (nextKeyword.test(lines[i])) break;
    if (lines[i].trim() !== "") last = i;
  }
  return last;
}

/**
 * Scan the `games:` block for the first reference to `newName` and return
 * the ordinal position (0-indexed) among games: entries. Returns -1 if
 * `newName` is not referenced.
 */
export function findFirstReferenceInGames(source, newName) {
  const gamesLine = findSectionLine(source, "games:");
  if (gamesLine === -1) return -1;
  const lines = source.split("\n");
  const boundary = new RegExp(`\\b${escapeRegExp(newName)}\\b`);
  let ordinal = 0;
  for (let i = gamesLine + 1; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (trimmed === "" || trimmed.startsWith("//")) continue;
    if (/^(let|assume|lemma|theorem|games|proof):\s*$/.test(trimmed)) break;
    if (boundary.test(trimmed)) return ordinal;
    ordinal++;
  }
  return -1;
}

/**
 * Return the line number just before `proof:`, after the Nth existing
 * top-level block of the given kind (`"Reduction"` or `"Game"`). `ordinal`
 * is the desired position among existing blocks of that kind.
 */
export function findOrderedBlockInsertionLine(source, kind, ordinal) {
  const lines = source.split("\n");
  const proofLine = findSectionLine(source, "proof:");
  const end = proofLine === -1 ? lines.length : proofLine;
  const header = new RegExp(`^\\s*${kind}\\s+\\w+\\s*\\(`);

  const blockStarts = [];
  let depth = 0;
  let inBlock = false;
  for (let i = 0; i < end; i++) {
    if (!inBlock && header.test(lines[i])) {
      blockStarts.push(i);
      inBlock = true;
      depth = 0;
    }
    if (inBlock) {
      for (const ch of lines[i]) {
        if (ch === "{") depth++;
        else if (ch === "}") {
          depth--;
          if (depth === 0) {
            inBlock = false;
            break;
          }
        }
      }
    }
  }

  if (ordinal <= 0 || blockStarts.length === 0) {
    return blockStarts.length === 0 ? end : blockStarts[0];
  }
  if (ordinal >= blockStarts.length) {
    return findBlockEndLine(source, blockStarts[blockStarts.length - 1]) + 1;
  }
  return blockStarts[ordinal];
}

function findBlockEndLine(source, startLine) {
  const lines = source.split("\n");
  let depth = 0;
  let started = false;
  for (let i = startLine; i < lines.length; i++) {
    for (const ch of lines[i]) {
      if (ch === "{") {
        depth++;
        started = true;
      } else if (ch === "}") {
        depth--;
        if (started && depth === 0) return i;
      }
    }
  }
  return lines.length - 1;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Insert `text` into CodeMirror `cm` at the given line (0-indexed), at
 * column 0. Ensures `text` ends with a newline.
 */
export function insertAtLine(cm, line, text) {
  const withNewline = text.endsWith("\n") ? text : text + "\n";
  cm.replaceRange(withNewline, { line, ch: 0 }, { line, ch: 0 });
}
