# latex-pdf-gen (paquete `latexgen`)

Genera PDFs a partir de plantillas LaTeX (`.tex`) con campos dinámicos tipados, escritos como marcadores `{{nombre?:tipo(argumento)}}`. El objetivo final es una aplicación web: el usuario sube la plantilla, la app arma un formulario con un control por tipo, valida los valores, compila con Tectonic y devuelve el PDF.

## Estado actual

* `main`: el core está completo y probado (`backend/src/latexgen/core/`: parser, escaping, renderer, compiler, service). 133 pruebas pasan.
* Rama `feature/backend/web` (subida, sin fusionar): capa FastAPI con `POST /parse`. `POST /generate` solo tiene su esquema `GenerateRequest`, en la rama `feature/backend/web-generate-endpoint`.
* Frontend (React + TypeScript con Vite): sin empezar.
* Decidido, sin implementar: `number` conservará el decimal tal como lo escribe el usuario (se pueden quitar los ceros a la derecha), sin pasar por `float`; los meses y días de `date` saldrán en un idioma elegible, español por defecto.
* Pendientes y discrepancias conocidas: `docs/guide/project.html`.

## Documentos

* **Guía técnica**: `docs/guide/` (abre `index.html`). Antes de tocar un sistema, lee su página:
  * `architecture.html`: capas, dependencias entre módulos, patrones y decisiones.
  * `pipeline.html`: flujo de `generate` paso a paso y la demostración interactiva.
  * `markers.html`: gramática de los marcadores y reglas de cada tipo.
  * `reference.html`: firmas y comportamiento de cada símbolo del core.
  * `errors.html`: jerarquía de excepciones y su traducción a HTTP.
  * `testing.html`: cómo correr las pruebas y qué cubren.
  * `web.html`: la capa web de la rama (en desarrollo).
  * `project.html`: entorno, git, discrepancias y pendientes.

## Documentación

* **Sincronización**: la guía sigue al código. Todo cambio de comportamiento, arquitectura o convención actualiza en el mismo commit la página afectada; nunca dejes la guía describiendo algo que ya no es así. Si una regla de trabajo cambia, actualiza también este archivo.
* **Fidelidad**: la guía solo describe lo implementado. Lo que vive en una rama o es un plan va marcado como tal (badge `rama`, callout `dev`).
* **Formato**: HTML en `docs/guide/`, sin dependencias externas (se abre con doble clic). Estilos y navegación compartidos en `guide.css` y `guide.js`; una página nueva se agrega a `GUIDE_PAGES` en `guide.js`. Diagramas en SVG en línea con las clases de `guide.css`.
* **Demostración**: `docs/guide/demo.js` es un port en JavaScript de `markers.py`, `parser.py`, `escaping.py` y `renderer.py`, con sus mismos mensajes de error. Si cambia alguno de esos archivos, el port cambia en el mismo commit y se vuelve a comparar con el Python real.
* **Este archivo** guarda solo instrucciones para el asistente; las explicaciones van en la guía.

## Cómo trabajar conmigo

* Diseño antes que código: propone la estructura (módulos, clases, firmas) y espera mi visto bueno antes de escribir.
* Entregas pequeñas, paso a paso. Quiero entender cada pieza antes de seguir: explica las librerías y herramientas nuevas cuando aparecen.
* Cuestiona mis supuestos si ves una opción mejor.
* Respuestas en español, claras y sin relleno. En la prosa no uses guiones como recurso de estilo.

## Reglas de código

* Código, comentarios, nombres de archivos y commits en inglés.
* Docstrings completos estilo PyDoc (Args, Returns, Raises) en toda función y clase, y comentarios que expliquen el porqué.
* Type hints en todas las firmas; cada módulo empieza con `from __future__ import annotations`.
* Arquitectura limpia con separación estricta de responsabilidades. Nada de sobreingeniería.
* **El core no depende de nada externo**: en `latexgen/core/` solo biblioteca estándar. Pydantic, FastAPI y PyYAML viven en la capa web. Las capas de afuera dependen del core, nunca al revés.
* La sintaxis de los marcadores vive solo en `markers.py` (`MARKER_PATTERN`); parser y renderer la comparten.
* Los errores del dominio heredan de `LatexGenError` (`exceptions.py`). Un error de LaTeX es un `CompileResult(ok=False)`, no una excepción; solo los problemas de entorno lanzan.
* `generate` vuelve a analizar la plantilla: no confíes en metadatos de campos que mande el cliente.
* Configuración que no es código, en YAML (capa web), no en constantes de Python.

## Ejecutar y verificar

Todo desde `backend/`, con el entorno virtual (`backend/.venv`, Python 3.11.3):

```
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"      # reinstala si cambian las dependencias
pytest                       # testpaths apunta a test/
```

* Tectonic 0.16.9 está en `C:\Tools\tectonic.exe` (en el PATH). Las pruebas que compilan de verdad se saltan solas si no lo encuentran.
* Pruebas: un módulo por módulo del core, en `test/unit/` y `test/integration/`. Sin Tectonic: `monkeypatch` de `subprocess.run` o un `Compiler` falso inyectado al service.
* Corre la suite completa ante cambios de lógica y antes de cada commit.

## Git

* Remoto `origin`: `https://github.com/grameromar/Contract-Document-Generation-Engine.git`.
* Cada pieza en su propia rama desde `main`: `feature/<area>-<tema>` para lo nuevo y `change/<area>-<tema>` para modificar lo existente (por ejemplo `feature/core-parser`, `change/core-markers`).
* Commits pequeños en inglés, uno por paso verificable.
* Merge a `main` solo con mi visto bueno. No hagas push sin que te lo pida.
* No reescribas ni borres las ramas web sin preguntarme: son trabajo en curso.
