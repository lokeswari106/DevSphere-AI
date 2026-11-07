# Recorded live demonstrations

These folders contain exports from the running DevSphere AI application using real Ollama `qwen3:8b` calls. They are saved demonstration evidence, not canned responses returned by the application. A fresh installation calls its configured model and can produce different results.

Read `status.json` for the recorded workflow state and actual sandbox counts. Each `evidence.json` preserves agent outputs, approvals, edits, events, file versions, review findings and test records. Failed, interrupted and cancelled attempts are deliberately retained. Approval comments explain corrections. Original model outputs remain available even when a reviewed proposal was changed before application.

Observed application tests on 7 November 2026: **URL Shortener 5 passed / 0 failed; E-commerce Studio 7 passed / 0 failed**. Both ran in the actual isolated Python sandbox, and their recorded source hashes match the exported approved files. The Node review scenario did not execute tests. These counts are separate from the platform's own test suite.

## What each scenario demonstrates

- **URL Shortener:** SRS, architecture and API design; generated API source; human corrections; independent quality and security analysis; a focused test workflow; actual isolated execution and a final report. The implementation is a small SQLite teaching example. Scalability is discussed as a future design, not a measured property.
- **E-commerce Studio:** requirement/design/code collaboration with a React and FastAPI teaching slice. Human review corrected authentication, ownership, transaction boundaries, stock handling and form wiring. The model's broad test draft exceeded its token limit; seven explicitly human-authored behavioral tests were then imported through approval and executed in the sandbox. Payments stay disabled. No real transaction or successful autonomous end-to-end generation is claimed.
- **Node Code Review:** real model code review and security analysis of the intentionally vulnerable classroom fixture. The source was never executed. Findings are static observations and AI hypotheses, not verified exploits or a security certification. Suggested fixes require review.

## Present the demo step by step

1. Start DevSphere using `docs/02-local-setup.md`; on the prepared computer it is already available at http://localhost:8010.
2. Sign in to your own account. On the prepared computer the generated demo account is stored privately in `.local/demo-account.json`; it is not part of this archive.
3. Open a saved project. Use Overview to show the timeline and inspect individual agent outputs.
4. Show Requirements, Architecture and Database and APIs. Explain the difference between the approved design and the deliberately bounded runnable teaching slice.
5. Open Code, compare file versions, and inspect the approval comments. Show how reviewed changes differ from the initial model output.
6. Open Code Review. Explain the severity and evidence labels; do not describe every AI finding as a verified vulnerability.
7. Open Testing and display the actual sandbox log and source hash. An old source result is not proof for a later source version.
8. Open Documentation. Read the final report separately from README/setup/testing documentation, then download Markdown or PDF.
9. If time permits, start a small new requirement. Model calls take time; approvals are part of the demonstration. Never present the saved exports as a new live generation.

The exported `approved-source` directories are artifacts to review, not host-side executables. Execute generated code/tests through the approved isolated runner. The static e-commerce catalogue and test inputs are labelled classroom fixtures; they are not business data. No coverage, throughput or production readiness score is inferred from passing functional tests.
