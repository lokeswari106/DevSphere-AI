// Repair notation only; keep entity names, types and relationships unchanged.
export function normalizeDiagramSource(value) {
  if (typeof value !== "string" || !value.trim()) throw new Error("Empty diagram");
  let source = value.trim().replace(/^\uFEFF/, "");
  const fence = source.match(/^```(?:mermaid)?\s*\n([\s\S]*?)\n```$/i);
  if (fence) source = fence[1].trim();
  if (source.length > 30000) throw new Error("Diagram is too large");
  if (/%%\s*\{|^---|^\s*click\s/im.test(source))
    throw new Error("Diagram configuration and interactions are not supported");
  if (/^erDiagram\b/.test(source)) {
    source = source.replace(
      /(^[ \t]*(?:[\w-]+|"[^"\n]+")\s*\{)([^{}]*)(\})/gm,
      (_, open, attributes, close) => open + attributes.replace(
        /^([ \t]*)([A-Za-z_]\w*)\s*:\s*([A-Za-z_][\w-]*(?:\([\d, ]+\))?(?:\[\])?)([^\n]*)$/gm,
        "$1$3 $2$4",
      ) + close,
    );
  }
  return source;
}
