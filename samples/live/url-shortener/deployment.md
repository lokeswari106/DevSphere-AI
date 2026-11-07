# Local deployment

Install requirements.txt and run uvicorn app:app --host 127.0.0.1 --port 8000. SQLite defaults to shortener.db; DB_PATH can override it. Review source before running it and use the approved sandbox for tests. Authentication, rate limiting and measured scaling are not implemented. Literal-address validation does not guarantee where a hostname resolves.