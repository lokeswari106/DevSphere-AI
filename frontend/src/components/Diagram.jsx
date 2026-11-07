import { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { normalizeDiagramSource } from "../lib/diagramSource";
import { renderDiagram } from "../lib/diagramRenderer";
let sequence = 0;
export default function Diagram({ source, title = "Architecture diagram" }) {
  const [error, setError] = useState("");
  const [svg, setSvg] = useState("");
  const [renderSource, setRenderSource] = useState(source);
  const [theme, setTheme] = useState(document.documentElement.dataset.theme);
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(document.documentElement.dataset.theme));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let alive = true;
    setError("");
    setSvg("");
    setRenderSource(source);
    const host = document.createElement("div");
    host.className = "diagram-render-buffer";
    host.setAttribute("aria-hidden", "true");
    // Measure even when this diagram is inside a closed activity disclosure.
    // Mermaid renders only into this owned, hidden host, removed on every path.
    document.body.appendChild(host);
    const render = async () => {
      try {
        const prepared = normalizeDiagramSource(source);
        if (alive) setRenderSource(prepared);
        const { svg } = await renderDiagram("diagram-" + ++sequence, prepared, host, theme === "dark");
        if (alive) {
          const clean = DOMPurify.sanitize(svg, {
            USE_PROFILES: { svg: true, svgFilters: true },
          });
          setSvg(clean);
        }
      } catch {
        if (alive)
          setError(
            "This diagram needs a syntax correction. You can inspect or download its source below.",
          );
      } finally {
        host.remove();
      }
    };
    render();
    return () => {
      alive = false;
      host.remove();
    };
  }, [source, theme]);
  function save(type) {
    const blob = new Blob([type === "svg" ? svg : renderSource], {
      type: type === "svg" ? "image/svg+xml" : "text/plain",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `diagram.${type}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  return (
    <section className="diagram-block">
      <div className="section-line">
        <h3>{title}</h3>
        <div>
          <button className="text-button" onClick={() => save("mmd")}>
            Source
          </button>
          {svg && (
            <button className="text-button" onClick={() => save("svg")}>
              Download SVG
            </button>
          )}
        </div>
      </div>
      {error && <p className="notice" role="status">{error}</p>}
      <div className="diagram" dangerouslySetInnerHTML={{ __html: svg }} />
      <details>
        <summary>View Mermaid source</summary>
        {renderSource !== source && <p className="muted">Attribute notation was adjusted for rendering. The original saved artifact is preserved.</p>}
        <pre>{renderSource}</pre>
        {renderSource !== source && <details><summary>Original saved source</summary><pre>{source}</pre></details>}
      </details>
    </section>
  );
}
