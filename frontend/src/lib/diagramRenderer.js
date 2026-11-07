import mermaid from "mermaid";

// Mermaid owns shared configuration. Keep parse, theme and render in one queue.
let queue = Promise.resolve();
export function renderDiagram(id, source, container, dark) {
  const operation = queue.then(async () => {
    mermaid.initialize({
      startOnLoad: false,
      suppressErrorRendering: true,
      securityLevel: "strict",
      theme: "base",
      // All diagram types must use SVG text, which survives SVG-only sanitizing.
      htmlLabels: false,
      maxTextSize: 30000,
      themeVariables: {
        fontFamily: '"Segoe UI", sans-serif',
        primaryColor: dark ? "#2b354b" : "#edf1fb",
        primaryTextColor: dark ? "#eeeeea" : "#24262b",
        primaryBorderColor: dark ? "#8a96b0" : "#77839f",
        secondaryColor: dark ? "#353a42" : "#f0f0ea",
        tertiaryColor: dark ? "#292c32" : "#faf9f6",
        lineColor: dark ? "#b9bdc5" : "#686967",
        textColor: dark ? "#eeeeea" : "#24262b",
        mainBkg: dark ? "#2b354b" : "#edf1fb",
        background: dark ? "#202328" : "#ffffff",
        rowOdd: dark ? "#24282e" : "#ffffff",
        rowEven: dark ? "#30343b" : "#f4f4ef",
      },
    });
    // Parsing first avoids Mermaid inserting a large error SVG into the page.
    const valid = await mermaid.parse(source, { suppressErrors: true });
    if (!valid) throw new Error("Invalid diagram syntax");
    return mermaid.render(id, source, container);
  });
  queue = operation.catch(() => {});
  return operation;
}
