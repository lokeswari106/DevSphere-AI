# Working with DevSphere AI, step by step

## 1. Enter your workspace

Open localhost:8010, create an account without an invitation token and sign in. The sidebar has Dashboard, New project, My projects, Code review and Settings. The light layout keeps the project brief and next approval visible. Dark mode is available from the sidebar.

## 2. Create a project

Choose a starter idea or New project. Enter a descriptive name, a requirement of at least 20 characters, language, framework and application type. Python/FastAPI, JavaScript/Node or React combinations, and Java standard-library projects are supported. Framework selection is validated against language. Start with a narrow vertical slice so the result fits the local model's context and can be tested.

## 3. Start a workflow

Open Overview, choose Full project generation and add optional constraints. Start workflow returns a persistent run ID. The timeline shows actual tasks and their outputs; polling updates the workspace every few seconds. Review-only, security-only, design, tests, documentation and repair paths reuse existing approved context instead of running every agent.

## 4. Review the plan and requirements

The orchestrator drafts milestones and task dependencies. Inspect the plan proposal, expand Edit this proposal to correct its JSON, or enter feedback and Request changes. Approve and continue saves an immutable approved document version. Reject stops the workflow. The requirement agent then produces functional requirements, business rules, stories, acceptance criteria, assumptions and open questions. Resolve scope ambiguity before approving.

The displayed plan communicates the engineering breakdown. The trusted orchestrator enforces the predefined workflow dependency graph; a model-generated plan cannot add arbitrary tools or bypass approval stages.

## 5. Review architecture, database and APIs

Architecture includes component boundaries, trade-offs and Mermaid diagrams. Database design includes entities, migration SQL text, ER notation and a validated OpenAPI document. View diagrams in Architecture and Database and APIs; download SVG or Mermaid source. SQL is a proposed artifact and is never automatically executed against your DevSphere database.

Human edits change the proposal hash. Approval is accepted only for the exact hash and project revision you inspected. Prior model output and the human edit audit record remain available. Changing a project brief invalidates downstream current documents; history remains preserved.

## 6. Inspect code changes

The code agent proposes multiple text files. Expand a file in the approval panel to see its difference from the approved version. Approve before files become current. In Code, choose a file from the explorer, use Monaco to edit it and select Propose changes. A second explicit approval applies the edit. Compare shows changes; Previous version retrieves an older revision.

Import source accepts selected text files, not ZIP archives or dependency folders. Relative paths, file sizes, allowed extensions and credential-like patterns are validated. An upload becomes a proposal, leaving the original local file unchanged.

## 7. Read review and security findings

The quality and security agents read the same approved source snapshot. Logical concurrency is used; model calls are serialized when the local provider concurrency setting is one. Findings show severity, file, available line number, explanation and suggested improvement. AI findings are hypotheses. Deterministic pattern observations are identified separately and do not establish exploitability. Review is not a penetration test or a complete dependency advisory audit.

## 8. Generate and run tests

The testing agent proposes files under `tests/`. Approve those files, then separately approve execution of the current source hash. The worker runs a fixed recipe inside a disposable container with no network and no host mounts. Results display actual process output and framework-reported counts. Missing counts remain unknown; zero tests is not a pass. Java uses a simple TestMain harness; coverage percentages are not invented.

A failed execution creates a checkpoint. Read the log, explain the desired repair and choose Request repair. The code agent receives the failure and review context; any changes and subsequent execution require new approvals. Continuing with disclosed failures is possible but the result remains failed in history.

## 9. Inspect documentation and deliver

Documentation uses approved artifacts and recorded test results. Open README, architecture, testing, deployment and final-report content. Download Markdown or PDF. The final delivery checkpoint confirms the current source hash. Export project creates a ZIP containing current approved files, current reports and a hash manifest. Generated applications require their own human review before deployment.

## 10. Continue an existing session

Open My projects and select the saved project. Versions show approved changes. Additional instructions can request a targeted code modification or documentation update. Cancel preserves approved artifacts and interrupts active or queued model work on the next coordinator tick (normally within two seconds). Task and execution history record the cancellation. A running sandbox is bounded by its time limit and may finish before cancellation cleanup. Failed stages can be explicitly retried. Do not run multiple sandbox workers in this single-worker release.

## Demonstration script for a college presentation

1. Explain the component diagram and show the PostgreSQL-backed project list.
2. Open a completed URL Shortener project. Show requirement → architecture → API → code traceability.
3. Show an original model proposal, the human correction and its new hash.
4. Show review/security findings and the actual isolated test log.
5. Export the project and report. Explain what remains a hypothesis.
6. Open the e-commerce example. Point out integer-cent prices, ownership rules and disabled payments.
7. Import the intentionally vulnerable Node sample and run review-only. Show that generation agents were skipped.
8. Start a small fresh requirement to demonstrate a real local model call. Wait for a checkpoint; generation time depends on hardware/model.

Allow 10–15 minutes for explaining saved real runs. Budget extra time for fresh model generation; do not present pre-recorded outputs as a new live execution. The evidence folder records when the saved runs actually occurred.
