# latexgen

Generate PDFs from LaTeX templates with dynamic, type-aware fields.

A template is a regular `.tex` document with markers such as `{{client}}` or
`{{amount:number}}`. `latexgen` discovers the fields, validates and escapes
each value according to its type, substitutes them, and compiles the result to
a PDF with [Tectonic](https://tectonic-typesetting.github.io/).

> **Status:** the core library is complete and tested on `main`. A FastAPI web
> layer is in progress on a separate branch; the frontend has not started.

## Requirements

- Python >= 3.10
- [Tectonic](https://tectonic-typesetting.github.io/) on your PATH
  (the LaTeX engine used to compile PDFs; installed separately, not via pip)

## Installation

From the `backend/` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Reinstall with the same command whenever the dependencies in `pyproject.toml`
change.

## Usage

```python
from latexgen.core.service import TemplateService

template = r"""\documentclass{article}
\begin{document}
Contract with {{client}} for \${{amount:number}}, starting {{start:date(%d/%m/%Y)}}.
Notes: {{notes?}}
\end{document}"""

service = TemplateService()          # uses TectonicCompiler by default
fields = service.parse(template)     # list[TemplateField], e.g. to build a form
pdf = service.generate(template, {
    "client": "Smith & Sons",        # special characters are escaped
    "amount": "1500000",             # rendered as 1,500,000
    "start": "2026-10-07",           # rendered as 07/10/2026
})                                   # "notes" is optional and left empty
open("contract.pdf", "wb").write(pdf)
```

## Marker syntax

`{{ name [?] [: type [(argument)] ] }}`

| Marker                          | Meaning                                         |
| ------------------------------- | ----------------------------------------------- |
| `{{name}}`                      | Required free-text field (`string`)             |
| `{{name?}}`                     | Optional field                                  |
| `{{age:number}}`                | Number, rendered with thousands separators      |
| `{{start:date(%d/%m/%Y)}}`      | ISO date input, rendered with a strftime format |
| `{{active:boolean}}`            | Rendered as `Sí` / `No`                         |
| `{{country:enum(MX,US,CA)}}`    | Must be one of the listed options               |

Every value is escaped for LaTeX, so user input cannot inject commands.
Domain errors (`ParseError`, `MissingFieldsError`, `InvalidFieldValueError`,
`CompileError`, `CompilerNotFoundError`) all derive from `LatexGenError`.

## Tests

From `backend/`:

```powershell
pytest
```

Tests that compile with the real Tectonic engine are skipped automatically
when it is not on the PATH.

## Documentation

The technical guide (in Spanish) lives in `docs/guide/`: open
`docs/guide/index.html` in a browser. It covers the architecture, the
execution flow with an interactive demo, the marker and type rules, the API
reference, errors, tests and the repository status.
