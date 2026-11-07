"""Conservative notation repair, not a claim of complete Mermaid validation."""

import re


def normalize_er_diagram(source: str) -> str:
    source = source.strip().lstrip("\ufeff")
    fence = re.fullmatch(r"```(?:mermaid)?\s*\n([\s\S]*?)\n```", source, re.I)
    if fence:
        source = fence[1].strip()
    if not re.match(r"^erDiagram\b", source):
        return source

    def entity(match):
        attributes = re.sub(
            r"^([ \t]*)([A-Za-z_]\w*)\s*:\s*([A-Za-z_][\w-]*(?:\([\d, ]+\))?(?:\[\])?)([^\n]*)$",
            r"\1\3 \2\4", match[2], flags=re.M,
        )
        return match[1] + attributes + match[3]

    return re.sub(
        r'(^[ \t]*(?:[\w-]+|"[^"\n]+")\s*\{)([^{}]*)(\})',
        entity, source, flags=re.M,
    )
