import Editor, { DiffEditor, loader } from "@monaco-editor/react";
import { useEffect, useState } from "react";
import * as monaco from "monaco-editor";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import JsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import CssWorker from "monaco-editor/esm/vs/language/css/css.worker?worker";
import HtmlWorker from "monaco-editor/esm/vs/language/html/html.worker?worker";
import TsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";
self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === "json") return new JsonWorker();
    if (label === "css") return new CssWorker();
    if (label === "html") return new HtmlWorker();
    if (["javascript", "typescript"].includes(label)) return new TsWorker();
    return new EditorWorker();
  },
};
loader.config({ monaco });
export const language = (path) =>
  ({
    py: "python",
    java: "java",
    json: "json",
    md: "markdown",
    sql: "sql",
    css: "css",
    html: "html",
    jsx: "javascript",
    js: "javascript",
    cjs: "javascript",
    mjs: "javascript",
    yaml: "yaml",
    yml: "yaml",
  })[path?.split(".").pop()] || "plaintext";
export default function CodeEditor({
  path,
  value,
  onChange,
  before,
  readOnly = false,
}) {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme);
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(document.documentElement.dataset.theme));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  const options = {
    minimap: { enabled: false },
    fontSize: 13,
    scrollBeyondLastLine: false,
    automaticLayout: true,
    readOnly,
    wordWrap: "on",
    padding: { top: 16 },
  };
  return before !== undefined ? (
    <DiffEditor
      theme={theme === "dark" ? "vs-dark" : "light"}
      height="440px"
      language={language(path)}
      original={before}
      modified={value}
      options={{
        ...options,
        readOnly: true,
        renderSideBySide: window.innerWidth > 800,
      }}
    />
  ) : (
    <Editor
      theme={theme === "dark" ? "vs-dark" : "light"}
      height="440px"
      path={path}
      language={language(path)}
      value={value}
      onChange={onChange}
      options={options}
    />
  );
}
