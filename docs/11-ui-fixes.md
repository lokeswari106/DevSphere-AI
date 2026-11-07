# Diagram, completion status and theme update

Verified on 7 November 2026 against the local DevSphere AI application.

## What changed

1. **ER diagram syntax.** Some saved model outputs used `id: UUID` inside an `erDiagram` entity. Mermaid requires `UUID id`. The viewer now repairs this specific notation before parsing. The backend also normalizes future database-design outputs and the database agent prompt includes a valid example. Relationships, attribute names and types remain intact. Existing saved artifacts and approval hashes are not rewritten.
2. **Contained diagram errors.** Parsing happens before rendering. Rendering uses a temporary owned container that is removed on success, failure and navigation. Unsupported syntax produces one inline explanation with downloadable source, instead of repeated Mermaid error graphics elsewhere on the page. This is not a general repair guarantee for arbitrary model-generated diagrams.
3. **Visible diagram labels.** Mermaid uses SVG text with `htmlLabels: false`, so labels survive SVG-only sanitization. The strict security setting and DOMPurify sanitization remain enabled. Diagram directives and interactive links are rejected. ER rows have explicit light/dark colors with checked text contrast.
4. **Accurate activity state.** Running/queued/testing work polls every three seconds; workflows waiting for approval poll every ten seconds. Completed, cancelled and idle workflows do not poll periodically. The Refresh button and returning focus to the window fetch current state. Terminal agent tasks no longer say that the agent is working. Stale requests are ignored when navigating between projects.
5. **Visual theme.** The initial indigo/cyan theme was subsequently replaced by the warm-white, charcoal and cobalt design described in [the visual style guide](12-visual-style.md). Theme selection persists after reload. Mobile layouts and reduced-motion preferences are supported.

The completion change concerns workflow status and refresh behavior. Generated applications are not automatically launched by this update. Approved generated-code tests still use the separate isolated runner.

## How to see the update

1. Open **http://localhost:8010** and refresh the page. If an old browser tab retains the previous bundle, use Command–Shift–R on macOS or Ctrl–Shift–R on Windows/Linux.
2. Sign in with your existing account.
3. Open a project and select **Architecture**, then **Database and APIs**. Previously saved colon-style ER attributes now render without editing the stored artifact.
4. Use **View Mermaid source** to inspect the normalized notation and, when changed, the original saved source. Use **Download SVG** to save the rendered diagram.
5. Switch between **Dark mode** and **Light mode** from the sidebar. On mobile, open the navigation menu first.
6. Open a completed project: the activity indicator should read **Completed**, and the cancellation action should be absent. **Refresh** retrieves current data on demand.

## Developer steps

No database migration is needed. From the project root:

```sh
npm ci --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
backend/.venv/bin/python scripts/start_local.py
```

Stop an already running instance through its own terminal before starting another on the same port. The setup guide covers prerequisites and Windows/Docker equivalents.

For backend tests, prepare the separate `devsphere_test` database and dedicated sandbox image as described in [testing](08-testing.md):

```sh
backend/.venv/bin/python -m pytest backend/tests -q --junitxml=docs/test-results/platform.xml
```

For the browser suite, run the local app, prepare the owned demonstration projects according to the testing guide, install Playwright Firefox if necessary, and run `npm run test:e2e` from `frontend/`.

## Observed validation

| Check | Result |
| --- | --- |
| Backend suite | 49 passed |
| Frontend unit/component suite | 22 passed |
| Firefox end-to-end suite | 8 passed |
| Saved diagram regression set | All 12 parsed and rendered in light and dark mode |
| ER label contrast | Checked against every rendered odd/even row fill in dark mode; at least 4.5:1 |
| Completed workflow | No periodic workflow request during the 4.5-second observation window; manual refresh worked |
| Production frontend and Docker builds | Succeeded |
| Visual inspection | Dashboard, mobile layout and ER diagrams checked from real browser screenshots |

The browser suite injects saved and malformed diagram fixtures into intercepted responses only for regression testing. It does not alter stored project documents or substitute simulated AI output into the live demonstration. Raw results are under `docs/test-results/`. The screenshot evidence is under `docs/screenshots/ui-refresh-*`.

This update did not rerun the real-model project-generation demonstrations or change their historical results. The previously generated Word/PDF college reports describe the initial delivery baseline; this file and the testing guide record the subsequent UI fixes.

## References

- [Mermaid ER attribute syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)
- [Mermaid parsing and rendering API](https://mermaid.js.org/config/usage.html)
- [Local setup](02-local-setup.md) and [operating guide](04-user-guide.md)
