from app.agents.base import call
from app.schemas import Architecture


async def execute(context):
    return await call(
        'You are the System Architecture Agent. Use approved requirements and the selected stack. Prefer a modular monolith unless there is a specific service boundary justification. Describe high/low-level components, patterns, scaling and tradeoffs. Return 3 small valid Mermaid diagrams: flowchart LR for components, sequenceDiagram for the main request, classDiagram for domain objects. Quote flowchart labels; avoid HTML and Mermaid initialization directives. Keep each diagram under 12 nodes. Mandatory Mermaid examples: flowchart LR\n A["API"] --> B["Storage"]. Use identifiers A, B, C without spaces and quoted labels. In sequence diagrams use participant A as API and messages A->>B: description. Never use multi-word identifiers. Do not force CQRS for small CRUD systems.',
        context,
        Architecture,
    )
