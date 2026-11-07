import importlib, json
import pytest
from unittest.mock import AsyncMock
from app.services.provider import provider
from app.schemas import (
    Plan,
    SRS,
    Architecture,
    DatabaseDesign,
    CodeBundle,
    Review,
    Delivery,
)

FIXTURES = {
    "orchestrator": {
        "summary": "Plan",
        "classification": "new_project",
        "milestones": ["Build"],
        "tasks": [
            {
                "name": "Requirements",
                "agent": "requirements",
                "depends_on": [],
                "acceptance": "Approved",
            }
        ],
        "constraints": ["Review required"],
    },
    "requirements": {
        "summary": "SRS",
        "functional_requirements": ["Create URL"],
        "non_functional_requirements": ["Validate input"],
        "business_rules": ["http only"],
        "user_stories": [
            {
                "role": "user",
                "action": "shorten",
                "benefit": "share",
                "acceptance_criteria": ["redirect works"],
            }
        ],
        "edge_cases": ["missing"],
        "complexity": "small",
        "open_questions": [],
        "assumptions": [],
    },
    "architecture": {
        "summary": "API",
        "style": "modular_monolith",
        "components": ["API"],
        "patterns": ["Repository"],
        "tradeoffs": ["single process"],
        "low_level_design": ["functions"],
        "scalability": ["index"],
        "diagrams": [{"title": "Flow", "mermaid": "flowchart LR\n A-->B"}],
    },
    "database": {
        "summary": "Store URLs",
        "entities": [
            {"name": "links", "fields": ["id text"], "keys": ["id"], "indexes": []}
        ],
        "migration_sql": "CREATE TABLE links (id text PRIMARY KEY);",
        "er_diagram": "erDiagram\n LINK { string id PK }",
        "openapi_json": json.dumps(
            {"openapi": "3.0.3", "info": {"title": "test", "version": "1"}, "paths": {}}
        ),
        "performance_notes": ["Index key"],
    },
    "code": {
        "summary": "Add",
        "files": [{"path": "app.py", "content": "def add(a,b):\n    return a+b\n"}],
        "setup_instructions": ["python app.py"],
        "limitations": [],
    },
    "review": {"summary": "Reviewed", "findings": [], "limitations": ["AI hypothesis"]},
    "security": {
        "summary": "Security review",
        "findings": [],
        "limitations": ["No advisory data"],
    },
    "tests": {
        "summary": "Test add",
        "files": [
            {
                "path": "tests/test_app.py",
                "content": "from app import add\ndef test_add():\n assert add(1,2)==3\n",
            }
        ],
        "setup_instructions": ["pytest"],
        "limitations": [],
    },
    "documentation": {
        "summary": "Documented",
        "readme_markdown": "# App",
        "architecture_markdown": "# Design",
        "testing_markdown": "Not run",
        "deployment_markdown": "Local only",
        "final_report_markdown": "# Report",
        "limitations": [],
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(FIXTURES))
async def test_specialized_agent_validates_and_uses_context(monkeypatch, name):
    fixture = FIXTURES[name]
    if name == "database":
        fixture = {k: v for k, v in fixture.items() if k != "openapi_json"}
        fixture["endpoints"] = [
            {
                "path": "/links/{code}",
                "method": "get",
                "summary": "Resolve a link",
                "request_fields": [],
                "response_fields": [
                    {
                        "name": "url",
                        "type": "string",
                        "required": True,
                        "description": "Target URL",
                    }
                ],
                "response_is_array": False,
                "success_status": 200,
            }
        ]
    fake = AsyncMock(
        return_value=(
            fixture,
            {
                "provider": "test_fixture",
                "model": "fixture",
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
    )
    monkeypatch.setattr(provider, "generate", fake)
    module = importlib.import_module(
        "app.agents."
        + ("testing_documentation" if name in {"tests", "documentation"} else name)
    )
    context = {"project_id": "test", "assignment": name, "files": []}
    if name == "documentation":
        context.update(
            {
                "approved_outputs": {"architecture": "Superseded conceptual design"},
                "reviews": [{"issue": "Historical advice"}],
                "user_decisions": [{"comment": "Old implementation-stage instruction"}],
                "recent_tests": [{"status": "passed", "passed": 5}],
                "instructions": "Document the current snapshot",
            }
        )
    result, usage = await module.execute(context)
    assert usage["provider"] == "test_fixture"
    if name == "database":
        from openapi_spec_validator import validate

        spec = json.loads(result["openapi_json"])
        validate(spec)
        assert (
            spec["paths"]["/links/{code}"]["get"]["parameters"][0]["required"] is True
        )
    else:
        assert result == FIXTURES[name]
    expected_context = (
        {
            k: v
            for k, v in context.items()
            if k not in {"approved_outputs", "reviews", "user_decisions"}
        }
        if name == "documentation"
        else context
    )
    assert fake.call_args.args[1] == expected_context
    assert fake.call_args.args[0]


@pytest.mark.asyncio
async def test_invalid_database_contract_rejected(monkeypatch):
    from app.agents.database import execute

    monkeypatch.setattr(
        provider,
        "generate",
        AsyncMock(
            return_value=(
                {**FIXTURES["database"], "openapi_json": '{"openapi":"3.0.3"}'},
                {},
            )
        ),
    )
    with pytest.raises(Exception):
        await execute({})


@pytest.mark.asyncio
async def test_generated_python_syntax_checked_without_executing(monkeypatch):
    from app.agents.code import execute

    monkeypatch.setattr(
        provider,
        "generate",
        AsyncMock(
            return_value=(
                {
                    **FIXTURES["code"],
                    "files": [{"path": "app.py", "content": "def broken(:"}],
                },
                {},
            )
        ),
    )
    with pytest.raises(SyntaxError):
        await execute({})


@pytest.mark.asyncio
async def test_testing_agent_cannot_rewrite_implementation(monkeypatch):
    from app.agents.testing_documentation import execute

    monkeypatch.setattr(
        provider, "generate", AsyncMock(return_value=(FIXTURES["code"], {}))
    )
    with pytest.raises(ValueError):
        await execute({"assignment": "tests"})


@pytest.mark.asyncio
@pytest.mark.parametrize("source,error", [
    ("def test_checkout():\n response = client.post('/api/products'))", SyntaxError),
    ("async def test_checkout():\n assert True", ValueError),
])
async def test_bad_generated_tests_rejected_with_draft_for_retry(monkeypatch, source, error):
    from app.agents.testing_documentation import execute
    draft = {**FIXTURES["tests"], "files": [{"path":"tests/test_app.py", "content":source}]}
    monkeypatch.setattr(provider, "generate", AsyncMock(return_value=(draft, {})))
    with pytest.raises(error) as exc:
        await execute({"assignment":"tests"})
    assert exc.value.failed_artifact == draft
