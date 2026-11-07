# Commerce Studio — reviewed teaching slice

Use Python 3.12 and Node 22.12+. Install `requirements.txt` in an isolated virtual environment, then run `uvicorn app:app --host 127.0.0.1 --port 8000`. In the frontend folder run `npm install` and `npm run dev`, then open http://localhost:5173. Vite proxies /api to port 8000.

The database path is configurable with DB_PATH and defaults to ecommerce.db. A fresh database contains an explicitly labelled classroom catalogue. Register with an email and a password of at least 12 characters. Sign in, add products, place an order, and inspect order history. Payment checks always return an explanatory 503; no charge occurs. The UI keeps its token only in memory.

The tests use pytest with FastAPI TestClient and a temporary DB_PATH. Execute generated tests only inside the approved DevSphere sandbox.

Limitations: local SQLite only; one active session per account; no email verification, reset, admin product management, production rate limiting, shipment or real payment integration. There are no measured scalability or security certification claims. DevSphere itself uses PostgreSQL; this teaching sample is separate.