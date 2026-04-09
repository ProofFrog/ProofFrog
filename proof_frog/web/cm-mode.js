// ── ProofFrog syntax highlighting mode ───────────────────────────────────────
// CodeMirror is loaded as a CDN global before this module runs.

/* global CodeMirror */

CodeMirror.defineMode("prooffrog", function () {
  var keywords = new Set([
    "Primitive","Scheme","Game","Reduction","proof","let","assume","theorem",
    "games","export","as","extends","compose","against","import","requires",
    "if","else","for","return","union","in","subsets","this",
    "adversary","calls","induction","from","to"
  ]);
  var types = new Set(["Bool","Void","Int","BitString","Set","Map","Array","ModInt"]);
  var atoms = new Set(["true","false","None"]);

  return {
    startState: function () { return { inBlockComment: false }; },
    token: function (stream, state) {
      // Inside a block comment — look for closing */
      if (state.inBlockComment) {
        while (!stream.eol()) {
          if (stream.match("*/")) { state.inBlockComment = false; return "comment"; }
          stream.next();
        }
        return "comment";
      }
      if (stream.eatSpace()) return null;
      // Block comment
      if (stream.match("/*")) { state.inBlockComment = true; return "comment"; }
      // Line comment
      if (stream.match("//")) { stream.skipToEnd(); return "comment"; }
      // Single-quoted string (import paths)
      if (stream.peek() === "'") {
        stream.next();
        while (!stream.eol() && stream.peek() !== "'") stream.next();
        if (!stream.eol()) stream.next();
        return "string";
      }
      // Numbers: binary and decimal
      if (stream.match(/0b[01]+/) || stream.match(/\d+/)) return "number";
      // Identifiers and keywords
      if (stream.match(/[A-Za-z_][A-Za-z0-9_]*/)) {
        var w = stream.current();
        if (keywords.has(w)) return "keyword";
        if (types.has(w)) return "type";
        if (atoms.has(w)) return "atom";
        return "variable";
      }
      // Operators
      if (stream.match("<-")) return "operator";
      if (stream.match(/[=!<>]=|&&|\|\|/)) return "operator";
      if (stream.match(/[+\-*\/|!<>=]/)) return "operator";
      stream.next();
      return null;
    }
  };
});

export function getModeForFile(path) {
  if (!path || path.startsWith(":inline:")) return null;
  var ext = path.split(".").pop();
  return ["primitive","scheme","game","proof"].includes(ext) ? "prooffrog" : null;
}
