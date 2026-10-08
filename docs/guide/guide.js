/* latexgen technical guide: shared navigation and widgets.
 *
 * Every page has the same skeleton (an empty sidebar, the main content and an
 * empty table of contents). This script fills the sidebar from GUIDE_PAGES,
 * builds the per-page table of contents from the h2/h3 headings, and wires the
 * theme toggle, the page filter, copy buttons and tabs.
 *
 * To add a page: create the HTML file with the same skeleton and add an entry
 * to GUIDE_PAGES (file, title, group, keywords; status is optional).
 */

const GUIDE_PAGES = [
  { file: "index.html", title: "Inicio", group: "Visión general",
    keywords: "resumen estado proyecto qué es componentes" },
  { file: "architecture.html", title: "Arquitectura", group: "Visión general",
    keywords: "capas dependencias módulos patrones factory strategy facade core" },
  { file: "pipeline.html", title: "Flujo de ejecución", group: "Visión general",
    keywords: "pipeline parse render compile secuencia demo interactiva generate" },
  { file: "markers.html", title: "Marcadores y tipos", group: "Core",
    keywords: "sintaxis regex marker string number date boolean enum opcional escape" },
  { file: "reference.html", title: "Referencia del core", group: "Core",
    keywords: "api firmas funciones clases parse_template get_escaper renderer compiler service models" },
  { file: "errors.html", title: "Errores", group: "Core",
    keywords: "excepciones jerarquía ParseError RenderError CompileError CompilerNotFoundError" },
  { file: "testing.html", title: "Pruebas", group: "Calidad",
    keywords: "pytest unit integration tectonic skipif monkeypatch stub" },
  { file: "web.html", title: "Capa web", group: "En desarrollo", status: "dev",
    keywords: "fastapi rama endpoint parse generate stash cors yaml http 422 503" },
  { file: "project.html", title: "Proyecto y git", group: "Proyecto",
    keywords: "entorno venv tectonic pyproject git remoto ramas stash discrepancias pendientes" },
];

const THEME_KEY = "latexgen-guide-theme";

function currentFile() {
  const name = location.pathname.split("/").pop();
  return name === "" ? "index.html" : decodeURIComponent(name);
}

function readStoredTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
}

function storeTheme(value) {
  try { localStorage.setItem(THEME_KEY, value); } catch (e) { /* storage unavailable */ }
}

function effectiveTheme() {
  const explicit = document.documentElement.dataset.theme;
  if (explicit) return explicit;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function toggleTheme() {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  storeTheme(next);
  document.querySelectorAll("[data-theme-label]").forEach((el) => {
    el.textContent = next === "dark" ? "Tema claro" : "Tema oscuro";
  });
}

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([key, value]) => {
    if (key === "text") node.textContent = value;
    else if (key === "html") node.innerHTML = value;
    else node.setAttribute(key, value);
  });
  (children || []).forEach((child) => node.appendChild(child));
  return node;
}

function brand() {
  return el("a", { class: "brand", href: "index.html" }, [
    el("span", { class: "brand-mark", text: "{ }" }),
    el("span", { text: "latexgen" }),
  ]);
}

function buildSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const here = currentFile();

  sidebar.appendChild(brand());
  sidebar.appendChild(el("p", { class: "brand-sub", text: "Guía técnica" }));

  const search = el("input", {
    class: "search",
    type: "search",
    placeholder: "Filtrar páginas…",
    "aria-label": "Filtrar páginas de la guía",
  });
  sidebar.appendChild(search);

  const navRoot = el("nav", { "aria-label": "Páginas de la guía" });
  sidebar.appendChild(navRoot);

  function render(filter) {
    navRoot.innerHTML = "";
    const query = filter.trim().toLowerCase();
    const matches = GUIDE_PAGES.filter((page) =>
      !query || (page.title + " " + page.keywords).toLowerCase().includes(query));
    if (!matches.length) {
      navRoot.appendChild(el("p", { class: "nav-empty", text: "Sin resultados." }));
      return;
    }
    let lastGroup = null;
    let list = null;
    matches.forEach((page) => {
      if (page.group !== lastGroup) {
        navRoot.appendChild(el("div", { class: "nav-group", text: page.group }));
        list = el("ul", { class: "nav-list" });
        navRoot.appendChild(list);
        lastGroup = page.group;
      }
      const link = el("a", { href: page.file }, [el("span", { text: page.title })]);
      if (page.status === "dev") link.appendChild(el("span", { class: "badge dev", text: "rama" }));
      if (page.file === here) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
      list.appendChild(el("li", {}, [link]));
    });
  }
  render("");
  search.addEventListener("input", () => render(search.value));
  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      const first = navRoot.querySelector("a");
      if (first) location.href = first.getAttribute("href");
    }
  });

  const themeBtn = el("button", { class: "btn", type: "button", "data-theme-label": "" });
  themeBtn.textContent = effectiveTheme() === "dark" ? "Tema claro" : "Tema oscuro";
  themeBtn.addEventListener("click", toggleTheme);
  sidebar.appendChild(el("div", { class: "sidebar-foot" }, [themeBtn]));
}

function buildTopbar() {
  const menu = el("button", { class: "btn", type: "button", "aria-label": "Abrir menú", text: "Menú" });
  menu.addEventListener("click", () => document.body.classList.toggle("nav-open"));
  const bar = el("header", { class: "topbar" }, [brand(), menu]);
  document.body.insertBefore(bar, document.body.firstChild);
  document.addEventListener("click", (event) => {
    if (!document.body.classList.contains("nav-open")) return;
    const sidebar = document.getElementById("sidebar");
    if (!sidebar.contains(event.target) && !menu.contains(event.target)) {
      document.body.classList.remove("nav-open");
    }
  });
}

function slugify(text) {
  return text.toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function buildToc() {
  const toc = document.getElementById("toc");
  const content = document.getElementById("content");
  if (!toc || !content) return;
  const headings = [...content.querySelectorAll("h2, h3")].filter((h) => !h.closest(".card, .api, .demo"));
  const used = new Set();
  headings.forEach((heading) => {
    if (!heading.id) {
      let id = slugify(heading.textContent);
      while (used.has(id) || document.getElementById(id)) id += "-x";
      heading.id = id;
    }
    used.add(heading.id);
    if (!heading.dataset.tocLabel) heading.dataset.tocLabel = heading.textContent.trim();
    heading.appendChild(el("a", { class: "anchor", href: "#" + heading.id, "aria-hidden": "true", text: "#" }));
  });
  const tocHeadings = headings.filter((h) => h.tagName === "H2" || h.dataset.toc === "yes");
  if (!tocHeadings.length) return;
  toc.appendChild(el("div", { class: "toc-title", text: "En esta página" }));
  const list = el("ul");
  tocHeadings.forEach((heading) => {
    const label = heading.dataset.tocLabel;
    const item = el("li", { class: heading.tagName === "H3" ? "sub" : "" }, [
      el("a", { href: "#" + heading.id, text: label }),
    ]);
    list.appendChild(item);
  });
  toc.appendChild(list);

  const links = [...toc.querySelectorAll("a")];
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((a) => a.classList.toggle("current", a.getAttribute("href") === "#" + entry.target.id));
    });
  }, { rootMargin: "0px 0px -70% 0px" });
  tocHeadings.forEach((heading) => observer.observe(heading));
}

function buildPageNav() {
  const content = document.getElementById("content");
  if (!content) return;
  const index = GUIDE_PAGES.findIndex((page) => page.file === currentFile());
  if (index < 0) return;
  const nav = el("nav", { class: "page-nav", "aria-label": "Página anterior y siguiente" });
  const prev = GUIDE_PAGES[index - 1];
  const next = GUIDE_PAGES[index + 1];
  if (prev) nav.appendChild(el("a", { href: prev.file }, [el("small", { text: "Anterior" }), el("span", { text: prev.title })]));
  if (next) nav.appendChild(el("a", { href: next.file, class: "next" }, [el("small", { text: "Siguiente" }), el("span", { text: next.title })]));
  content.appendChild(nav);
}

function addCopyButtons() {
  document.querySelectorAll("pre").forEach((pre) => {
    if (pre.dataset.nocopy !== undefined) return;
    const button = el("button", { class: "btn copy-btn", type: "button", text: "Copiar" });
    button.addEventListener("click", async () => {
      const text = pre.querySelector("code") ? pre.querySelector("code").innerText : pre.innerText;
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = "Copiado";
      } catch (e) {
        button.textContent = "No se pudo copiar";
      }
      setTimeout(() => { button.textContent = "Copiar"; }, 1400);
    });
    pre.appendChild(button);
  });
}

function wireTabs() {
  document.querySelectorAll(".tabs").forEach((tabs) => {
    const buttons = [...tabs.querySelectorAll(".tab-list button")];
    const panels = [...tabs.querySelectorAll(".tab-panel")];
    function select(index) {
      buttons.forEach((b, i) => b.setAttribute("aria-selected", String(i === index)));
      panels.forEach((p, i) => { p.hidden = i !== index; });
    }
    buttons.forEach((button, i) => {
      button.setAttribute("role", "tab");
      button.addEventListener("click", () => select(i));
    });
    select(0);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  buildTopbar();
  buildSidebar();
  buildToc();
  buildPageNav();
  addCopyButtons();
  wireTabs();
});
