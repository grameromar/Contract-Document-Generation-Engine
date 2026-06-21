"""Single source of truth for the dynamic-field marker syntax.

Both the parser (which discovers fields) and the renderer (which substitutes
them) rely on the same marker grammar. Defining it here once keeps the two from
drifting apart: a change to the syntax is made in this module alone.

A marker has the form ``{{ name [?] [: type [ (argument) ] ] }}`` where:

- ``name`` is an identifier (letters, digits, underscore);
- a trailing ``?`` on the name marks the field as optional (TypeScript-style,
  e.g. ``{{note?}}`` or ``{{age?:number}}``); without it the field is required;
- ``type`` is optional and defaults to ``string``;
- ``argument`` is optional and carries the enum options (``enum(a,b,c)``) or
  the date format (``date(%d/%m/%Y)``).
"""

from __future__ import annotations

import re

# Capture groups:
#   1 = name
#   2 = optional flag  ("?" when present, marking the field optional)
#   3 = type           (optional; absent means "string")
#   4 = argument       (optional; the text inside the parentheses)
MARKER_PATTERN = re.compile(
    r"\{\{\s*(\w+)\s*(\?)?\s*(?::\s*(\w+)\s*(?:\(([^)]*)\))?\s*)?\}\}"
)