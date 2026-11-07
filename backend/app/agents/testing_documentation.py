from app.agents.base import call
from app.schemas import CodeBundle, Delivery
from app.services.source_validation import validate_generated_bundle


async def execute(context):
    if context["assignment"] == "tests":
        result, usage = await call(
            """You are the Testing and Documentation Agent in TEST GENERATION mode. Generate actual unit and integration tests for the exact provided implementation and acceptance criteria. Test the real exported functions/routes, not copies or stubs of the implementation. Cover happy path and invalid input. Python tests must be synchronous def test_* functions (no pytest.mark.asyncio or async def); use pytest and FastAPI TestClient, put tests/test_app.py; import app from the actual module. Prefer 5-10 meaningful tests; avoid inventing endpoints. Match actual success status codes and request/response shapes. Isolate database state for each test with pytest fixtures; never rely on test order or reuse registrations in a shared database. Never grant admin rights through public registration; seed an authorized admin fixture through the test database. Node tests use node:test and node:assert/strict with supertest for Express, files tests/*.test.cjs; import actual app.cjs. Java tests use a plain public class TestMain with main and explicit AssertionError on failure, in tests/TestMain.java; print a TESTS summary only from actual counters. Available Python packages fastapi, httpx, pytest, sqlalchemy, pydantic, bcrypt and jose; Node packages express and supertest. No dependency downloads or network requests. No scripts, system commands, .env, configuration rewrites or deletion of existing tests. Do not claim execution occurred. Return only test files and explanations.""",
            context,
            CodeBundle,
        )
        validate_generated_bundle(result, tests_only=True)
        return result, usage
    # Historical designs and old review advice are useful for engineering stages,
    # but can describe features that the approved implementation later changed.
    # Delivery documents describe the current snapshot and its recorded tests.
    delivery_context = {
        key: value
        for key, value in context.items()
        if key not in {"approved_outputs", "reviews", "user_decisions"}
    }
    return await call(
        """You are the Testing and Documentation Agent in DOCUMENTATION mode. Document the CURRENT provided files, not an imagined or historical design. Follow the current instructions and stage feedback. Write five concise Markdown sections, each at most100words and2500characters. No source-code dumps, large tables or repeated specifications. Include setup commands matching actual files. Describe only components present in source. The recent_tests records are the authority for actual execution; old README comments cannot override those results. Never invent pass counts, coverage, benchmarks or verified security findings. If tests have not run say not run; if failed report the failure. Distinguish human review contributions from model work using the provided instructions. Do not list an already implemented feature as remaining work. The final report should summarize only this project's deliverables, actual test result and limitations. Markdown only, no raw HTML.""",
        delivery_context,
        Delivery,
    )
