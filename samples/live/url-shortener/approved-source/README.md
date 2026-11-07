# URL Shortener teaching API

Real Ollama draft with recorded human review fixes to URL parsing, DB initialization, connection closure and atomic collision handling.
Use Python 3.12. Install requirements.txt in a virtual environment.
Run: DB_PATH=shortener.db uvicorn app:app --host 127.0.0.1 --port 8000
POST /links accepts JSON {"url":"https://example.com"} and returns short_code with 201.
GET /r/{code} returns 307 and increments clicks. GET /links/{code} returns original_url and click_count. Missing codes return 404.
The database is initialized automatically. Existing records are preserved.
Only HTTP(S) hostnames and global literal IPs are accepted. The server never fetches or resolves destinations; DNS safety is not guaranteed.
Local SQLite only, no authentication, rate limit or measured high-scale performance. No payments are relevant to this project.
Tests have not run yet; see the subsequent sandbox records.
