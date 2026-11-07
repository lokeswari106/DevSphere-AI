# Testing and validation record

Recorded on **7 November 2026**. These are observed outcomes, not model estimates. Platform tests, provider simulations and real-model demonstrations are separate evidence categories.

## Platform results

| Check | Observed result | Evidence |
| --- | --- | --- |
| Backend Pytest | 57 passed, 0 failed | `test-results/platform.xml` |
| Frontend Vitest | 26 passed | `test-results/frontend.json` |
| Firefox end-to-end | 11 passed | Dashboard/workspace, import/approval/editor, mobile navigation, Mermaid/Swagger, saved diagrams, error containment, completion polling and theme checks |
| Provider fault simulation | 4 expected outcomes | `provider-simulation-results.json` |
| Frontend production build | Succeeded | Vite build; lazy editor/diagram chunks remain large |
| Docker application build | Succeeded | `Dockerfile` builds compiled React and FastAPI |
| Compose services | App and PostgreSQL healthy | `/health/ready` returned 200 on the isolated Compose validation port 8012 |
| Public HTTPS | Authenticated access and secure cookie verified | Unauthenticated projects 401; authenticated projects 200; registration disabled |

Pytest emitted a dependency deprecation warning about the Starlette TestClient/httpx integration. It did not fail the suite. No coverage percentage or load-test capacity is claimed.

The latest UI regression run covers all 12 saved diagrams in both themes, the reported colon-style ER attributes, missing SVG labels, dark ER row contrast, invalid-diagram cleanup and completed-workflow polling. See [the update notes](11-ui-fixes.md). The earlier Compose, provider-fault and demonstration baselines are retained below; additional live checks for this update are recorded in the final section.

## What the backend tests establish

Authentication, JWT/cookie behavior, CSRF and origin rejection; project ownership and soft deletion; schema and language/framework validation; proposal hashes and optimistic revisions; immutable file versions and comparisons; path/extension/size/credential-pattern validation; approved-only exports; one active run per project; prerequisite enforcement; provider retry records; stage barriers; review-only routing; interrupted lease recovery; upstream context invalidation; editable proposals; documentation regeneration; concrete OpenAPI responses; Markdown/PDF output; and test approval requirements.

The cancellation check starts a waiting provider call, cancels the workflow through the API, and verifies that the coordinator interrupts the call and records cancelled task/execution states without launching another retry.

The documentation-agent check verifies that current source, instructions and actual test results are retained while historical design/review/approval context is excluded from the delivery prompt. Final Markdown sections also have explicit schema size limits.

Agent unit tests use explicitly labelled structured fixtures. Their purpose is repeatability, not demonstrating model intelligence. Real model execution is evidenced independently by saved live project records.

## Actual sandbox tests

The sandbox suite executes real containerized processes. It verifies denied network access, a read-only root, absent application secrets and Docker socket, timeout termination, an actual failing assertion, Python result counts, Node's built-in test runner and a Java TestMain harness. The trusted image and fixed entrypoint are used; untrusted source is never executed by FastAPI or imported on the application host.

Container isolation tests reduce specific risks. They do not prove resistance to every kernel/container escape. The runner uses one personal Docker context and a separate process. There is no automatic dependency installation from generated package files.

## Reproduce backend checks

Prepare a **separate** PostgreSQL database named `devsphere_test` beside the configured live database. The test fixture asserts that name before resetting tables. Build `devsphere-sandbox:1` in the configured personal context, then run:

```sh
backend/.venv/bin/python -m pytest backend/tests -q --junitxml=docs/test-results/platform.xml
```

Never change the test fixture to target a valuable database. Database migrations should also be applied to a fresh installation with `alembic upgrade head`; Compose startup exercises that path.

## Reproduce UI checks

```sh
npm ci --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
```

Start localhost:8010 and create the local demonstration account/projects with `scripts/demo_session.py`. From the frontend directory install Playwright Firefox if needed, then run `npm run test:e2e`. The tests create their own owned source-import project; they do not submit fake AI research. Screenshots under `docs/screenshots` are captured from the running app.

## Reproduce provider failure checks

With the Postman CLI installed, run the local simulation on port 4319:

```sh
postman simulation run postman/simulations/provider.sim.yaml --port 4319 --no-history --output ndjson
```

In a second terminal:

```sh
backend/.venv/bin/python scripts/check_provider_simulation.py
```

The real HTTP adapter receives valid structured JSON, HTTP 503, malformed JSON and a delayed response. It returns/raises the expected result in each case. This fixture is never configured as the live application's model provider. See the adjacent simulation context file for limitations and traffic observations.

## Real model demonstrations

The live account contains URL Shortener, E-commerce Studio and Node Code Review projects. Saved exports and the final status record belong under `samples/live`. Their task history preserves real Ollama calls, rejected proposals, human edits and retries. Generated application test outcomes must be read from their own sandbox records; platform test counts do not imply that generated applications passed.

The URL shortener is a local SQLite teaching slice; high-scale behavior is a design extension without a benchmark. E-commerce payments are disabled and no financial transactions occur. The Node input is an intentionally vulnerable classroom fixture for review only, not a deployed service or a verified runtime exploit.

## Measurement definitions

- Task completion: persisted agent-task status, with superseded/interrupted/failed attempts kept separate.
- Workflow completion: final approval accepted and run marked completed; human waiting time is included in wall-clock workflow duration.
- Agent duration: recorded elapsed invocation time, which can include waiting for the model semaphore.
- Retry count: attempt index in agent execution history, not an invented reliability score.
- Test pass rate: passed/total for an actual nonzero test execution tied to its source hash. Unknown counts remain unknown.
- API failures: observed HTTP/error records for tested requests; no overall production failure rate is inferred.

## Unverified environments

The native live demonstration was run on macOS. Docker image and Compose startup were checked on the dedicated local Linux VM. Windows/Linux setup instructions are provided, but a full fresh-machine installation on each operating system was not performed. The optional OpenAI adapter was not live-tested with a paid key. No permanent third-party cloud deployment or internet-scale load test is claimed.

## Direct review and portable startup update

The current suite also covers quick-review routing and persisted replacement code, syntax-repair retries, fixed authentication libraries inside the sandbox, pasted/uploaded input, source-preserving suggestions, and launcher credential/context configuration. The repaired user e-commerce snapshot separately passed 24 actual sandbox tests. See [the repair record](13-reviews-and-test-repair.md) and [one-command local setup](../RUN_LOCALLY.md).

The one-command launcher was exercised with a separate Compose project on port 8013. Account creation, approved source import, one actual sandbox test and a real Ollama review/security workflow succeeded. After a graceful stop and restart, the same account, project, both source files, passing test result and completed review remained available. The temporary verification stack was stopped without deleting its volumes. [Portable verification receipt](portable-verification.json).

This check used macOS for the launcher, Linux containers for the application/database/sandbox, and the existing native Ollama service. The default bundled Ollama model-download path and a fresh Windows installation were not exercised. The direct pasted-code demonstration used real model calls; [its receipt](review-repair-verification.json) distinguishes that evidence from mocked automated agent tests.
