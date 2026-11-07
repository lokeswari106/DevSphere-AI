"""Exercise the real adapter against the local Postman fixture, not a live model."""

import sys, asyncio, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:4319/ollama"
os.environ["MODEL_TIMEOUT"] = "1"
import httpx
from pydantic import ValidationError
from app.services.provider import Provider
from app.schemas import Plan


async def run():
    results = []
    p = Provider()
    async with httpx.AsyncClient() as c:
        for mode, expected in [
            ("ok", None),
            ("failure", httpx.HTTPStatusError),
            ("malformed", ValidationError),
            ("timeout", httpx.ReadTimeout),
        ]:
            r = await c.post(
                "http://127.0.0.1:4319/ollama/control", json={"mode": mode}
            )
            r.raise_for_status()
            try:
                output, usage = await p.generate(
                    "Plan a test fixture", {"fixture": True}, Plan
                )
                assert expected is None and output["classification"] == "test_fixture"
                results.append({"case": mode, "outcome": "valid structured response"})
            except Exception as exc:
                if expected is None or not isinstance(exc, expected):
                    raise
                results.append({"case": mode, "outcome": type(exc).__name__})
        await c.post("http://127.0.0.1:4319/ollama/control", json={"mode": "ok"})
    (ROOT / "docs/provider-simulation-results.json").write_text(
        json.dumps(
            {
                "basis": "Real HTTP adapter against test-only Postman simulation",
                "cases": results,
            },
            indent=2,
        )
    )
    print(json.dumps(results))


asyncio.run(run())
