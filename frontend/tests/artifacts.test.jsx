import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, it, expect } from "vitest";
import { Artifact, Status, Markdown, Empty } from "../src/components/Artifacts";
afterEach(cleanup);
describe("Honest engineering output", () => {
  it("shows the actual pending state", () => {
    render(<Status value="awaiting_approval" />);
    expect(screen.getByText("Awaiting Approval")).toBeInTheDocument();
  });
  it("renders untrusted source as text", () => {
    const { container } = render(
      <Artifact value={"<script>alert(1)</script>"} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
  });
  it("does not enable raw HTML in Markdown", () => {
    const { container } = render(
      <Markdown>{'<img src=x onerror="alert(1)" />'}</Markdown>,
    );
    expect(container.querySelector("img")).toBeNull();
  });
  it("explains empty test state", () => {
    render(<Empty title="No tests have run">Approve execution first.</Empty>);
    expect(screen.getByText("No tests have run")).toBeVisible();
    expect(screen.getByText("Approve execution first.")).toBeVisible();
  });
  it("handles null and empty artifacts", () => {
    render(<Artifact value={[]} />);
    expect(screen.getByText("None recorded.")).toBeVisible();
  });
});
