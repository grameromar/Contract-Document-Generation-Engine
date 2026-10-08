/* JavaScript port of the latexgen core, used by the interactive demos.
 *
 * It mirrors, function by function, these Python sources:
 *   backend/src/latexgen/core/markers.py   MARKER_PATTERN
 *   backend/src/latexgen/core/parser.py    parse_template, _build_field, _split_options
 *   backend/src/latexgen/core/escaping.py  escape_latex and the type escapers
 *   backend/src/latexgen/core/renderer.py  Renderer.render, _is_empty
 * and reproduces their error messages. If one of those files changes, this port
 * must change in the same commit.
 *
 * Known differences (documented in the demo itself):
 *   - date: only "YYYY-MM-DD" input and the directives %Y %m %d %y %j %% are
 *     ported. Python also accepts other ISO 8601 forms (e.g. "20240115") and
 *     every strftime directive.
 *   - number: only ASCII digits. Python's \d also matches other Unicode digits.
 */
(function (root) {
  "use strict";

  // markers.py: groups 1=name, 2=optional flag, 3=type, 4=argument.
  // Python's \w is Unicode-aware for str patterns; [\p{L}\p{N}_] matches it.
  const MARKER_SOURCE =
    String.raw`\{\{\s*([\p{L}\p{N}_]+)\s*(\?)?\s*(?::\s*([\p{L}\p{N}_]+)\s*(?:\(([^)]*)\))?\s*)?\}\}`;

  function markerPattern() {
    return new RegExp(MARKER_SOURCE, "gu");
  }

  // parser.py
  const VALID_TYPES = ["string", "number", "date", "boolean", "enum"];

  class LatexGenError extends Error {
    constructor(message) { super(message); this.name = this.constructor.name; }
  }
  class ParseError extends LatexGenError {}
  class RenderError extends LatexGenError {}
  class MissingFieldsError extends RenderError {
    constructor(missingFields) {
      super("Missing required fields: " + missingFields.join(", "));
      this.missingFields = missingFields.slice();
    }
  }
  class InvalidFieldValueError extends RenderError {
    constructor(fieldName, reason) {
      super(`Invalid value for field '${fieldName}': ${reason}`);
      this.fieldName = fieldName;
      this.reason = reason;
    }
  }

  function field(name, type, required, options, dateFormat) {
    return { name, type, required, options: options || [], date_format: dateFormat == null ? null : dateFormat };
  }

  function sameField(a, b) {
    return a.name === b.name && a.type === b.type && a.required === b.required &&
      a.date_format === b.date_format &&
      a.options.length === b.options.length && a.options.every((o, i) => o === b.options[i]);
  }

  function splitOptions(rawArgument) {
    if (!rawArgument) return [];
    return rawArgument.split(",").map((o) => o.trim()).filter((o) => o.length > 0);
  }

  function buildField(name, declaredType, rawArgument, required) {
    if (declaredType === "enum") {
      const options = splitOptions(rawArgument);
      if (!options.length) return field(name, "string", required);
      return field(name, "enum", required, options);
    }
    if (declaredType === "date") {
      const dateFormat = rawArgument ? rawArgument.trim() : null;
      return field(name, "date", required, [], dateFormat || null);
    }
    return field(name, declaredType, required);
  }

  function parseTemplate(content) {
    const seen = new Map();
    for (const match of content.matchAll(markerPattern())) {
      const name = match[1];
      const required = match[2] === undefined;
      const declaredType = (match[3] || "string").toLowerCase();
      const rawArgument = match[4] === undefined ? null : match[4];

      if (!VALID_TYPES.includes(declaredType)) {
        throw new ParseError(
          `Unsupported type '${declaredType}' for field '${name}'. ` +
          `Valid types: ${VALID_TYPES.slice().sort().join(", ")}.`);
      }
      const built = buildField(name, declaredType, rawArgument, required);
      if (seen.has(name)) {
        if (!sameField(seen.get(name), built)) {
          throw new ParseError(`Field '${name}' is declared inconsistently across markers.`);
        }
        continue;
      }
      seen.set(name, built);
    }
    return [...seen.values()];
  }

  // escaping.py
  const LATEX_SPECIAL_CHARACTERS = {
    "\\": "\\textbackslash{}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
  };

  // Single pass, like str.translate: each character is looked up once.
  function escapeLatex(text) {
    let out = "";
    for (const ch of text) out += Object.prototype.hasOwnProperty.call(LATEX_SPECIAL_CHARACTERS, ch)
      ? LATEX_SPECIAL_CHARACTERS[ch] : ch;
    return out;
  }

  const DEFAULT_DATE_FORMAT = "%Y-%m-%d";
  const TRUTHY = ["true", "1", "yes", "y", "si", "sí", "on", "verdadero"];
  const FALSY = ["false", "0", "no", "n", "off", "falso", ""];
  const NUMBER_PATTERN = /^-?\d+(\.\d+)?$/;

  // Python repr() of a str, enough for the messages the core produces.
  function pyRepr(value) {
    if (value === null || value === undefined) return "None";
    if (typeof value === "boolean") return value ? "True" : "False";
    if (typeof value === "number") return String(value);
    const s = String(value);
    if (s.includes("'") && !s.includes('"')) return '"' + s.replace(/\\/g, "\\\\") + '"';
    return "'" + s.replace(/\\/g, "\\\\").replace(/'/g, "\\'") + "'";
  }

  function pyStr(value) {
    if (value === null || value === undefined) return "None";
    if (typeof value === "boolean") return value ? "True" : "False";
    return String(value);
  }

  function groupThousands(intDigits) {
    const negative = intDigits.startsWith("-");
    const body = negative ? intDigits.slice(1) : intDigits;
    return (negative ? "-" : "") + body.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  // Python's repr(float) combined with the "," format spec.
  function formatPythonFloat(number) {
    if (Object.is(number, -0)) return "-0.0";
    const magnitude = Math.abs(number);
    if (magnitude !== 0 && (magnitude >= 1e16 || magnitude < 1e-4)) {
      // Scientific notation, exponent padded to two digits like Python.
      return number.toExponential().replace(/e([+-])(\d)$/, "e$10$2");
    }
    let text = String(number);
    if (!text.includes(".")) text += ".0";
    const [intPart, fracPart] = text.split(".");
    return groupThousands(intPart) + "." + fracPart;
  }

  function escapeString(value) {
    if (value === null || value === undefined) return "";
    return escapeLatex(pyStr(value));
  }

  function escapeNumber(value) {
    const digits = pyStr(value).replace(/,/g, "").trim();
    if (!NUMBER_PATTERN.test(digits)) {
      throw new Error(`Expected a numeric value, received: ${pyRepr(value)}`);
    }
    const number = Number(digits);
    if (digits.includes(".")) return formatPythonFloat(number);
    // int(float(digits)): exact integer value of the double.
    return groupThousands(BigInt(Math.trunc(number)).toString());
  }

  function pad(n, width) { return String(n).padStart(width, "0"); }

  function dayOfYear(y, m, d) {
    return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(y, 0, 1)) / 86400000) + 1;
  }

  function makeDateEscaper(dateFormat) {
    const format = dateFormat || DEFAULT_DATE_FORMAT;
    return function escapeDate(value) {
      const text = pyStr(value).trim();
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
      let valid = false;
      let y = 0, m = 0, d = 0;
      if (match) {
        y = Number(match[1]); m = Number(match[2]); d = Number(match[3]);
        const probe = new Date(Date.UTC(y, m - 1, d));
        valid = y >= 1 && probe.getUTCFullYear() === y && probe.getUTCMonth() === m - 1 && probe.getUTCDate() === d;
      }
      if (!valid) throw new Error(`Expected an ISO date (YYYY-MM-DD), received: ${pyRepr(value)}`);
      return format.replace(/%(.)/g, (whole, directive) => {
        switch (directive) {
          case "Y": return pad(y, 4);
          case "m": return pad(m, 2);
          case "d": return pad(d, 2);
          case "y": return pad(y % 100, 2);
          case "j": return pad(dayOfYear(y, m, d), 3);
          case "%": return "%";
          default: return `⟨%${directive}: no portado⟩`;
        }
      });
    };
  }

  function escapeBoolean(value) {
    if (typeof value === "boolean") return value ? "Sí" : "No";
    const text = pyStr(value).trim().toLowerCase();
    if (TRUTHY.includes(text)) return "Sí";
    if (FALSY.includes(text)) return "No";
    throw new Error(`Cannot interpret value as boolean: ${pyRepr(value)}`);
  }

  function makeEnumEscaper(options) {
    const optionsRepr = "[" + options.map(pyRepr).join(", ") + "]";
    return function escapeEnum(value) {
      const text = pyStr(value);
      if (!options.includes(text)) {
        throw new Error(`Value '${text}' is not among the allowed options: ${optionsRepr}`);
      }
      return escapeLatex(text);
    };
  }

  function getEscaper(fieldType, options, dateFormat) {
    if (fieldType === "enum") {
      if (!options || !options.length) return escapeString;
      return makeEnumEscaper(options);
    }
    if (fieldType === "date") return makeDateEscaper(dateFormat || DEFAULT_DATE_FORMAT);
    const simple = { string: escapeString, number: escapeNumber, boolean: escapeBoolean };
    if (simple[fieldType]) return simple[fieldType];
    throw new Error(`No escaper available for type: ${fieldType}`);
  }

  // renderer.py
  function isEmpty(value) {
    return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
  }

  function render(template, fields, values) {
    const missing = fields.filter((f) => f.required && isEmpty(values[f.name])).map((f) => f.name);
    if (missing.length) throw new MissingFieldsError(missing);

    const escaped = new Map();
    for (const f of fields) {
      const raw = values[f.name];
      if (isEmpty(raw)) { escaped.set(f.name, ""); continue; }
      const escaper = getEscaper(f.type, f.options, f.date_format || DEFAULT_DATE_FORMAT);
      try {
        escaped.set(f.name, escaper(raw));
      } catch (err) {
        throw new InvalidFieldValueError(f.name, err.message);
      }
    }
    return template.replace(markerPattern(), (whole, name) => (escaped.has(name) ? escaped.get(name) : whole));
  }

  const api = {
    MARKER_SOURCE, markerPattern, VALID_TYPES, parseTemplate, escapeLatex, getEscaper, render,
    ParseError, RenderError, MissingFieldsError, InvalidFieldValueError,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.LatexgenDemo = api;
})(typeof window !== "undefined" ? window : globalThis);
