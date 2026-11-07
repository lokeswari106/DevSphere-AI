# DevSphere AI visual style

The current design uses warm white, charcoal and cobalt blue. It replaces the previous indigo/cyan gradients with flat surfaces, fine dividers and a restrained accent color.

## Palette

| Role | Light | Dark |
| --- | --- | --- |
| Page | `#FAF9F6` | `#191B1F` |
| Surface | `#FFFFFF` | `#202328` |
| Main text | `#24262B` | `#EEEEEA` |
| Secondary text | `#686967` | `#ABADAE` |
| Dividers | `#DEDFD8` | `#373B40` |
| Link/selection | `#294FC3` | `#A9BAFF` |
| Primary button | `#2448B5` | `#335AC6` |

Green, amber and red remain reserved for success, review and error states. Status text accompanies every colored indicator.

## Layout and type

- Georgia gives the dashboard greeting and sign-in headline an editorial character. System sans-serif keeps forms, navigation and engineering outputs easy to scan. Monospace is reserved for small labels and metadata. No external font service is required.
- Project history uses rows with fine separators. Example projects share a single divided panel. Buttons and fields use small corner radii.
- Cobalt identifies primary actions and selected navigation. Neutral surfaces keep the diagrams, code and project outputs prominent.
- On small screens, example projects stack vertically and the sidebar opens as a drawer. The menu button exposes its expanded state, and tapping the backdrop closes the drawer.
- Dark mode uses neutral graphite. Mermaid diagrams and Monaco's editor/comparison view follow the selected theme. Theme choice persists after reload.

## Inspect locally

1. Open `http://localhost:8010` and refresh. Use Command–Shift–R or Ctrl–Shift–R if an old tab retains the previous JavaScript bundle.
2. Check the dashboard, New Project form and an existing project workspace.
3. Switch Light/Dark mode in the sidebar, then inspect diagrams and the Code tab.
4. At a mobile width, use the top-left navigation button; tap outside the drawer to close it.

Source: `frontend/src/styles.css`, `frontend/src/main.jsx`, `frontend/src/components/CodeEditor.jsx`, `frontend/src/lib/diagramRenderer.js` and `frontend/index.html`. To rebuild, run `npm run build --prefix frontend`; the running FastAPI server serves the updated static build.

## Validation and screenshots

The production frontend build succeeded. The frontend suite passed **22 tests** and the Firefox suite passed **8 checks**, including dark Monaco rendering, mobile drawer behavior, theme persistence, all 12 saved diagrams, invalid-diagram containment and completed-workflow polling. Backend behavior was not changed or retested for this visual update.

Actual screenshots, captured from the running app:

- [Light dashboard](screenshots/editorial-dashboard.png)
- [Dark dashboard](screenshots/editorial-dashboard-dark.png)
- [Mobile dashboard](screenshots/editorial-mobile.png)
- [New Project](screenshots/editorial-new-project.png)
- [Sign in](screenshots/editorial-sign-in.png)
- [Dark code comparison](screenshots/editorial-code-dark.png)

The Word/PDF college reports retain their original delivery screenshots. This guide records the current visual design.
