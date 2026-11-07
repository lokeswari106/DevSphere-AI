# Free demonstration and deployment

## Local, with no paid AI account

The verified demonstration uses native Ollama and the open local model `qwen3:8b`. The application, database and test runner remain on the student's computer. Electricity, hardware and internet are still required. OpenAI is optional and is not assumed to be free.

## Temporary free HTTPS demonstration

A Cloudflare Quick Tunnel can expose only the authenticated DevSphere HTTP application to an evaluator. It creates a temporary `trycloudflare.com` address without a domain or hosting account. The laptop, application, database, model and tunnel must remain running. The address changes when restarted; it is not permanent hosting. [Cloudflare Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)

The recommended public demo uses a second HTTP process on port 8011 with `WORKER_ENABLED=false`, `REGISTRATION_ENABLED=false`, `SECURE_COOKIE=true`, and `APP_ORIGIN` set to the exact HTTPS tunnel origin. The main local process continues coordinating workflows. Both use the same personal PostgreSQL database. Create the evaluator's own account locally first, and share its credentials privately. Do not put passwords in a report or URL.

1. Finish local installation and verify `/health/ready`.
2. Install `cloudflared` from Cloudflare's official package or a trusted package manager.
3. Run `cloudflared tunnel --url http://127.0.0.1:8011 --protocol http2 --no-autoupdate`.
4. Copy the generated HTTPS origin.
5. Start the public process from `backend`, with these environment overrides:

```sh
APP_ORIGIN=https://YOUR-TEMPORARY-ADDRESS.trycloudflare.com \
SECURE_COOKIE=true REGISTRATION_ENABLED=false WORKER_ENABLED=false \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8011 --no-proxy-headers
```

6. Visit the HTTPS address and confirm that unauthenticated project requests return 401.
7. Sign in with the locally created evaluator account. Demonstrate saved real runs and optionally a new approved workflow.
8. Stop the public process and tunnel after the presentation. Database/model/Docker ports must never be forwarded.

The application currently supports a small trusted classroom audience. In-memory rate limiting is per application process and remote IP handling is deliberately conservative. An internet-scale multi-tenant launch would require further hardening, abuse controls, tenant quotas, monitoring and a stronger isolation service.

## Independent cloud hosting option

The repository builds as one web image plus PostgreSQL. A platform such as Render can host the web container and a managed PostgreSQL provider such as Neon can hold the data. Supply `DATABASE_URL` with the provider's required TLS settings, a random JWT secret, exact HTTPS `APP_ORIGIN`, secure cookies and a configured model provider.

A free web tier can sleep and has an ephemeral filesystem; model execution and a privileged Docker sandbox are not provided by that tier. Keep a separate controlled runner or disable test execution honestly. Native localhost Ollama is not reachable from an unrelated cloud web host. You would need a reachable model service or a paid API. The free Render database offer is time-limited; do not rely on it for a permanent college archive. Verify quotas before choosing a provider. [Render free-tier limitations](https://render.com/docs/free), [Neon plans](https://neon.com/pricing)

No cloud account, credit card or office subscription is required by the local route. No claim is made that an always-on hosted model, persistent database and arbitrary-code sandbox can all be supplied permanently for free.

## Operational checklist

- Keep secrets in environment configuration, never source control.
- Apply Alembic migrations and verify readiness before serving users.
- Keep one workflow coordinator and one sandbox worker in this release.
- Back up PostgreSQL privately; source exports are not full database backups.
- Rebuild pinned images/dependencies after review and rerun meaningful checks.
- Use actual test logs and current source hashes in a demonstration.
