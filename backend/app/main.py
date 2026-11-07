import asyncio, logging, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from app.config import settings, ROOT
from app.db import engine
from app.api.routes import router
from app.services.orchestration import dispatcher

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


@asynccontextmanager
async def lifespan(app):
    stop = asyncio.Event()
    task = asyncio.create_task(dispatcher(stop)) if settings().worker_enabled else None
    yield
    stop.set()
    if task:
        await task


def create_app():
    app = FastAPI(
        title="DevSphere AI",
        version="1.0.0",
        description="Versioned multi-agent engineering with human approval and isolated testing.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def metadata(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        size = request.headers.get("content-length")
        if size and (not size.isdigit() or int(size) > 1000000):
            return JSONResponse(
                {"code": "payload_too_large", "message": "Request exceeds 1 MB"},
                status_code=413,
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; worker-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
        )
        if request.url.path in {"/docs", "/redoc"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'"
            )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(req, exc):
        return JSONResponse(
            {
                "code": "request_error",
                "message": exc.detail,
                "request_id": req.state.request_id,
            },
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(req, exc):
        return JSONResponse(
            {
                "code": "validation_error",
                "message": "Check the submitted fields",
                "details": [
                    {"location": list(e["loc"]), "message": e["msg"]}
                    for e in exc.errors()
                ],
                "request_id": req.state.request_id,
            },
            status_code=422,
        )

    @app.exception_handler(ValueError)
    async def value_error(req, exc):
        return JSONResponse(
            {
                "code": "invalid_artifact",
                "message": str(exc)[:500],
                "request_id": req.state.request_id,
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(req, exc):
        logging.getLogger("devsphere.api").error(
            "Unhandled %s request_id=%s",
            type(exc).__name__,
            getattr(req.state, "request_id", "unknown"),
        )
        return JSONResponse(
            {
                "code": "internal_error",
                "message": "The operation failed. Check the server log using the request ID.",
                "request_id": getattr(req.state, "request_id", "unknown"),
            },
            status_code=500,
        )

    @app.get("/health/live", tags=["System"])
    def live():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/health/ready", tags=["System"])
    def ready():
        with engine.connect() as conn:
            conn.execute(text("SELECT id FROM users LIMIT 1"))
        return {"status": "ok", "version": "1.0.0"}

    app.include_router(router)
    from fastapi.openapi.utils import get_openapi

    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method not in {"get", "post", "put", "delete", "patch"}:
                    continue
                if path.startswith("/api/") and path not in {
                    "/api/auth/login",
                    "/api/auth/register",
                }:
                    operation["security"] = [{"BearerAuth": []}]
                operation["description"] = (
                    operation.get("description", "")
                    + " Cookie sessions are also supported. Cookie-authenticated writes require X-CSRF-Token from /api/auth/me. Bearer requests do not need CSRF headers."
                )
                for code, description in {
                    "401": "Authentication required",
                    "403": "Origin or CSRF rejected",
                    "404": "Owned resource not found",
                    "409": "Revision conflict or unmet dependency",
                    "422": "Invalid input or artifact",
                    "429": "Rate limit exceeded",
                }.items():
                    operation["responses"][code] = {
                        "description": description,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["code", "message"],
                                    "properties": {
                                        "code": {"type": "string"},
                                        "message": {"type": "string"},
                                        "request_id": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
    dist = ROOT / "frontend/dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def frontend(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Endpoint not found")
            return FileResponse(dist / "index.html")

    return app


app = create_app()
