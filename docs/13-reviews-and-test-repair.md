# Direct code review and e-commerce test repair

## Paste or upload code

1. Open **Code review** in the sidebar.
2. Choose **Paste code** and provide a filename and source, or choose **Upload files** and select text source files.
3. Select the language. Optionally name the review and describe its focus.
4. Select **Save & review code**. This authorizes storing the initial source in a new owned project, then starts the `quick_review` workflow.
5. The quality and security agents inspect the same source snapshot. No generated source is executed by this workflow. It does not require unrelated requirements, architecture or code-generation stages.
6. Inspect findings in **Code Review**. Each finding identifies its file, line where available, severity, rationale and suggested fix. **Source context** shows nearby lines from the matching stored file version.
7. Use **Copy code** or **Download suggestion** to take a proposed replacement. A suggestion is not automatically applied or claimed to have passed tests. If no replacement was provided, the UI says so.

Supported inputs: JavaScript, Python, Java and related text files, at most 60 files, 100 KB each, 750 KB total. Archives, binary files, unsafe paths and common private-key/token patterns are rejected. Files are sent to the configured model provider. Remove credentials before submission.

The older full review workflow remains available. Existing projects can use **Review current code** for the shorter analysis route. Original file versions remain available and outdated findings are marked as earlier-source findings.

## API contract

The new screen reuses ownership-checked project, file-import and approval endpoints. It creates a new project, proposes the submitted source, approves that exact initial snapshot as explicitly requested by **Save & review code**, and posts:

```http
POST /api/projects/{project_id}/execute
Content-Type: application/json

{"workflow_type":"quick_review","instructions":"Review the supplied source and suggest replacement functions."}
```

The response is `202` with a run ID and status URL. Missing source or an active workflow returns `409`. Poll `/workflow` while queued/running and fetch `/reviews` after completion. Findings retain `file_id`, `file_path`, `line_number`, `improved_code`, `evidence_status` and `source_current`. JWT/cookie ownership, CSRF validation, rate limits and existing import approval checks apply. No migration was needed.

## Why the e-commerce tests failed

The user's latest run stopped during collection because `tests/test_app.py` contained extra closing parentheses. The preceding run failed importing `bcrypt`. Inspection also found unsupported asynchronous pytest tests, shared database state, incorrect success-status assumptions, an unquoted SQL `Order` table, missing SQLite row mapping and broken cart/checkout logic.

The repair corrects the implementation and tests together. It also prevents public admin self-registration, validates product/quantity inputs, checks cart and order ownership, protects stock updates in a transaction, handles invalid tokens, and clearly labels payments as a simulation. Tests provision their administrator through a trusted isolated database fixture; they do not weaken the admin requirement.

The repaired source is a new project revision. Previous source, agent outputs and failed executions remain in history. Maintenance authorization is recorded as assistant work requested in the conversation, not a fabricated UI click or autonomous model output.

The resumed workflow's documentation-model attempts failed output-size validation. Those failures remain recorded. A concise maintenance-authored report documents the repaired snapshot, the actual 24-test result and its limitations; it was approved under the same explicit maintenance authorization. The project is complete, but the history does not claim that its final repair or report was generated autonomously.

## Preventing recurrence

- Generated Python code **and generated Python tests** are parsed before proposals are accepted. Parsing does not import or execute source.
- Syntax failures retain the invalid draft for the orchestrator's bounded retry.
- The test generator is instructed to use synchronous pytest/TestClient tests, isolated data and actual API contracts. Unsupported async tests are rejected with retry feedback.
- The trusted sandbox now includes pinned `bcrypt` and `python-jose` dependencies. New runtime dependencies are installed only during a reviewed image build, never from untrusted project requirements. See [bcrypt](https://pypi.org/project/bcrypt/) and [python-jose](https://pypi.org/project/python-jose/).
- Collection errors are explained separately in the Testing tab, while the actual framework log is preserved.

## Evidence and limits

The repaired e-commerce snapshot passed **24 real tests** in the constrained sandbox, including authentication, validation, privilege checks, cart operations, ownership, atomic checkout, history and simulated payments. The stored project test run has the exact source hash and actual execution log. These tests do not establish production readiness or complete security coverage.

A separate live demonstration submitted `pricing.js` through the Firefox paste form and ran both agents using the real configured Ollama model. The result included concrete replacement functions. Findings remain model hypotheses: for example, one response described empty-array division as throwing an error, whereas JavaScript yields `NaN` in this example. No generated replacement was automatically executed or represented as verified.

Automated browser input tests intercept only workflow submission to avoid repeated model calls; agent tests use explicitly labelled fixtures. Live model evidence is stored separately from those checks. Screenshots are under `docs/screenshots/review-*`.

Machine-readable results are in [review-repair-verification.json](review-repair-verification.json). The repaired source can also be downloaded from `output/E-commerce-Repaired-Project.zip`; this is the generated FastAPI application, while the main DevSphere source archive contains the engineering platform.
