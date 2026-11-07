import { describe, it, expect } from "vitest";
import mermaid from "mermaid";
import { normalizeDiagramSource } from "../src/lib/diagramSource";
import fixtures from "./fixtures/saved-diagrams.json";

mermaid.initialize({ startOnLoad: false, securityLevel: "strict", suppressErrorRendering: true });
describe("Saved diagrams use actual Mermaid grammar", () => {
  it.each(fixtures)("parses $name after conservative normalization", async ({ source }) => {
    expect(await mermaid.parse(normalizeDiagramSource(source), { suppressErrors: true })).toBeTruthy();
  });
  it("reproduces the reported colon error and preserves ER meaning when repaired", async () => {
    const source = 'erDiagram\n User ||--o{ Order : "has"\n User {\n id: UUID PK\n email: string "Contact email"\n balance: decimal(10,2)\n }';
    expect(await mermaid.parse(source, { suppressErrors: true })).toBe(false);
    const repaired = normalizeDiagramSource(source);
    expect(repaired).toContain('User ||--o{ Order : "has"');
    expect(repaired).toContain('UUID id PK');
    expect(repaired).toContain('string email "Contact email"');
    expect(repaired).toContain('decimal(10,2) balance');
    expect(await mermaid.parse(repaired, { suppressErrors: true })).toBeTruthy();
  });
  it("does not reinterpret class members or sequence messages", () => {
    for (const source of ['classDiagram\nclass User {\n +id: UUID\n}', 'sequenceDiagram\nA->>B: id: UUID'])
      expect(normalizeDiagramSource(source)).toBe(source);
  });
  it("unwraps a complete code fence but rejects configuration and interaction directives", () => {
    expect(normalizeDiagramSource('```mermaid\nerDiagram\nUser {\nid: UUID\n}\n```')).toContain('UUID id');
    for (const source of ['%%{init: {}}%%\ngraph LR', '---\nconfig:\n---\ngraph LR', 'flowchart LR\nclick A "https://example.com"'])
      expect(() => normalizeDiagramSource(source)).toThrow();
    expect(() => normalizeDiagramSource('x'.repeat(30001))).toThrow();
  });
});
