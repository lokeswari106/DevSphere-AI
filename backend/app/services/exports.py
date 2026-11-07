import io, json, html
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def markdown_document(kind, payload, section="final_report"):
    if kind == "documentation":
        return payload.get(section + "_markdown", "")
    out = ["# " + kind.replace("_", " ").title()]
    for key, value in payload.items():
        out.append("\n## " + key.replace("_", " ").title())
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            out.extend(
                "- " + (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                for v in value
            )
        else:
            out.append("```json\n" + json.dumps(value, indent=2) + "\n```")
    return "\n\n".join(out)


def pdf_document(markdown):
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []
    for line in markdown.splitlines():
        if not line.strip():
            story.append(Spacer(1, 5))
            continue
        style = (
            styles["Heading1"]
            if line.startswith("# ")
            else styles["Heading2"]
            if line.startswith("## ")
            else styles["BodyText"]
        )
        text = line.lstrip("# ").replace("`", "")
        # Split long tokens to keep generated paths and JSON within page margins.
        text = " ".join(
            token
            if len(token) < 70
            else " ".join(token[i : i + 65] for i in range(0, len(token), 65))
            for token in text.split(" ")
        )
        story.append(Paragraph(html.escape(text), style))

    def footer(c, doc):
        c.setFont("Helvetica", 8)
        c.drawString(42, 25, "DevSphere AI | " + str(doc.page))

    SimpleDocTemplate(
        buf, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
