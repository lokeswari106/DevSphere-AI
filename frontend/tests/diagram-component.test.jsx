import React from "react";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, it, expect, vi } from "vitest";
vi.mock("../src/lib/diagramRenderer", () => ({ renderDiagram: vi.fn() }));
import { renderDiagram } from "../src/lib/diagramRenderer";
import Diagram from "../src/components/Diagram";

beforeEach(() => { vi.resetAllMocks(); document.documentElement.dataset.theme = "light"; });
afterEach(cleanup);
it("clears a previous SVG when a new diagram fails and confines its message", async () => {
  renderDiagram.mockResolvedValueOnce({ svg: '<svg><text>Working diagram</text><script>alert(1)</script></svg>' });
  const { container, rerender } = render(<Diagram source="flowchart LR\nA-->B" />);
  await waitFor(() => expect(container.querySelector('.diagram svg')).not.toBeNull());
  expect(container.querySelector('script')).toBeNull();
  renderDiagram.mockRejectedValueOnce(new Error('Parse failure'));
  rerender(<Diagram source="not a diagram" />);
  await screen.findByText(/This diagram needs a syntax correction/);
  expect(container.querySelector('.diagram svg')).toBeNull();
  expect(document.querySelector('.diagram-render-buffer')).toBeNull();
});
it("renders again when the selected theme changes", async () => {
  renderDiagram.mockResolvedValue({ svg: '<svg><text>Diagram</text></svg>' });
  const { container } = render(<Diagram source="flowchart LR\nA-->B" />);
  await waitFor(() => expect(container.querySelector('.diagram svg')).not.toBeNull());
  document.documentElement.dataset.theme = "dark";
  await waitFor(() => expect(renderDiagram).toHaveBeenLastCalledWith(expect.any(String), expect.any(String), expect.any(HTMLElement), true));
});
