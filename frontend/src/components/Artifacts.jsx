import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { lazy, Suspense } from "react";
import { label } from "../api";
const Diagram = lazy(() => import("./Diagram"));
export function Markdown({ children }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {String(children || "")}
      </ReactMarkdown>
    </div>
  );
}
export function Artifact({ value, name = "" }) {
  if (value == null) return null;
  if (typeof value === "string") {
    if (["mermaid", "er_diagram"].includes(name))
      return (
        <Suspense fallback={<p>Loading diagram…</p>}>
          <Diagram source={value} />
        </Suspense>
      );
    if (name.endsWith("markdown")) return <Markdown>{value}</Markdown>;
    if (["migration_sql", "openapi_json", "improved_code"].includes(name))
      return <pre className="code-block">{value}</pre>;
    return <p className="artifact-text">{value}</p>;
  }
  if (Array.isArray(value))
    return value.length ? (
      <div>
        {value.map((v, i) => (
          <div
            className={typeof v === "string" ? "list-item" : "artifact-item"}
            key={i}
          >
            <Artifact value={v} />
          </div>
        ))}
      </div>
    ) : (
      <p className="muted">None recorded.</p>
    );
  if (value.mermaid)
    return (
      <Suspense fallback={<p>Loading diagram…</p>}>
        <Diagram title={value.title} source={value.mermaid} />
      </Suspense>
    );
  return (
    <div>
      {Object.entries(value)
        .filter(([k]) => !["files", "usage"].includes(k))
        .map(([k, v]) => (
          <section className="artifact-section" key={k}>
            <h3>{label(k)}</h3>
            <Artifact value={v} name={k} />
          </section>
        ))}
    </div>
  );
}
export function Status({ value }) {
  return (
    <span className={`status status-${value}`}>
      <span />
      {label(value || "draft")}
    </span>
  );
}
export function Empty({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
