# Simulation context — DevSphere provider failures

## Purpose and source

This test-only simulation implements the Ollama POST `/api/chat` envelope used by `backend/app/services/provider.py`. The official source contract is https://docs.ollama.com/api/chat. It stands in for a local Ollama service such as http://127.0.0.1:11434. It does not simulate model quality or the full Ollama API.

No shared/office Postman workspace is used. Published-owner mock discovery was unavailable without login; the local fixture was built from the primary provider documentation. Live demonstration runs use the real Ollama service, not this simulation.

## Reproduce

Start in one terminal from the project root:

```sh
postman simulation run postman/simulations/provider.sim.yaml --port 4319 --no-history --output ndjson
```

In another terminal, using the configured Python environment:

```sh
backend/.venv/bin/python scripts/check_provider_simulation.py
```

The script sets `OLLAMA_BASE_URL=http://127.0.0.1:4319/ollama` and a one-second timeout only in its own process. It switches the local fixture through success, 503, malformed JSON and 2.5-second delay cases, then restores success. It does not change `.env` or the running live application. Stop the simulation with Ctrl+C in its own terminal.

## Observations

On 2026-11-07 the real HTTP adapter made four `/api/chat` calls to route key `ollama`. The cases produced a valid structured result, HTTPStatusError, Pydantic ValidationError and ReadTimeout respectively. The final delayed server response completed after the client had already timed out. Recorded outcomes are in `docs/provider-simulation-results.json`.

## Assumptions and limits

- Port 4319 must be available. There is no proxy forwarding to a real provider in this setup.
- Restart the simulation after editing a handler; mocks do not hot reload.
- Only the model HTTP dependency is simulated. PostgreSQL and Docker isolation are checked separately.
- A passing simulation proves adapter handling of these fixtures, not live model reliability, token limits or provider billing behavior.
- Fixture source includes no real credentials or private project data.
