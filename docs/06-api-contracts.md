# API contracts

Interactive Swagger: http://localhost:8010/docs. Complete OpenAPI 3.1 document: [openapi.json](openapi.json). Request and response fields are generated from Pydantic contracts and mapped record definitions.

## Authentication

Register/login returns an HttpOnly SameSite=Strict cookie, an access token for API clients and a CSRF value. The React client keeps the CSRF value in memory and sends X-CSRF-Token on cookie-authenticated writes. API clients may use Authorization: Bearer TOKEN. Never place a token in a URL. `/api/auth/me` restores the browser session. Tokens expire after eight hours; refresh-token rotation is not included. Logout clears the browser cookie and does not revoke an already copied bearer token.

## Common responses

201 creates a resource; 202 queues work or proposes a change; 204 returns no body. Errors use code, message, optional details and request_id. 401 requires login, 403 rejects CSRF/origin, 404 hides unowned resources, 409 signals stale revisions or unmet dependencies, 422 signals invalid data and 429 rate limits requests. Results use project ownership checks on every protected route.

## Endpoints

| Method | Path | Responsibility |
| --- | --- | --- |
| GET | `/health/live` | Live |
| GET | `/health/ready` | Ready |
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Me |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/settings` | Capabilities |
| POST | `/api/projects` | Create Project |
| GET | `/api/projects` | Projects |
| GET | `/api/projects/{project_id}` | Project |
| PUT | `/api/projects/{project_id}` | Update Project |
| DELETE | `/api/projects/{project_id}` | Delete Project |
| POST | `/api/projects/{project_id}/execute` | Execute |
| GET | `/api/projects/{project_id}/workflow` | Workflow |
| GET | `/api/projects/{project_id}/status` | Status |
| POST | `/api/projects/{project_id}/cancel` | Cancel |
| POST | `/api/projects/{project_id}/retry` | Retry |
| GET | `/api/projects/{project_id}/agents` | Tasks |
| GET | `/api/projects/{project_id}/agent-tasks` | Tasks |
| POST | `/api/projects/{project_id}/design` | Start Architecture |
| POST | `/api/projects/{project_id}/database-design` | Start Database |
| POST | `/api/projects/{project_id}/generate-code` | Start Code |
| POST | `/api/projects/{project_id}/review` | Start Review |
| POST | `/api/projects/{project_id}/security-analysis` | Start Security |
| POST | `/api/projects/{project_id}/generate-tests` | Start Tests |
| POST | `/api/projects/{project_id}/documentation` | Start Documentation |
| GET | `/api/projects/{project_id}/requirements` | Requirements |
| POST | `/api/projects/{project_id}/requirements` | Edit Requirement |
| GET | `/api/projects/{project_id}/files` | Files |
| GET | `/api/projects/{project_id}/files/{file_id}` | File |
| PUT | `/api/projects/{project_id}/files/{file_id}` | Change File |
| POST | `/api/projects/{project_id}/files/import` | Import Files |
| GET | `/api/projects/{project_id}/files/{file_id}/diff` | Diff |
| GET | `/api/projects/{project_id}/reviews` | Reviews |
| GET | `/api/projects/{project_id}/tests` | Tests |
| POST | `/api/projects/{project_id}/run-tests` | Request Tests |
| GET | `/api/projects/{project_id}/documents` | Documents |
| GET | `/api/projects/{project_id}/documents/{document_id}/download` | Download Document |
| GET | `/api/projects/{project_id}/versions` | Versions |
| GET | `/api/projects/{project_id}/events` | Events |
| GET | `/api/projects/{project_id}/approvals` | Approvals |
| PUT | `/api/projects/{project_id}/approvals/{approval_id}` | Edit Proposal |
| POST | `/api/projects/{project_id}/approvals/{approval_id}/decision` | Decide |
| GET | `/api/projects/{project_id}/export` | Export |

## Approval protocol

1. GET workflow or approvals; read the pending artifact, `artifact_hash` and `base_revision`.
2. Inspect the complete artifact. PUT approval may edit eligible structured artifacts and returns a new hash.
3. POST decision with `decision`, `artifact_hash`, `expected_revision` and optional `comment`.
4. A matching hash/revision commits the artifact or queues approved execution. A stale request returns 409 and must be reviewed again.

```json
{"decision":"approve","artifact_hash":"<64-character proposal SHA-256>","expected_revision":3,"comment":"Reviewed design and limitations"}
```

## Polling and idempotency

Poll workflow/status about every three seconds while active. Starting a second active run returns 409. Repeating an already resolved approval returns 409 rather than applying it twice. A request-ID header correlates errors; no generic Idempotency-Key implementation is claimed. A disconnected browser can reload the stored run and artifacts.

## Input boundaries

Project descriptions are limited to 12,000 characters. File proposals support at most 60 files, 100 KB per file and 750 KB combined source. Text source only; archives, executable binaries, absolute paths, traversal, hidden credential files and common private-key/token patterns are rejected. Projects larger than the configured model context budget stop explicitly rather than silently dropping a source file.
