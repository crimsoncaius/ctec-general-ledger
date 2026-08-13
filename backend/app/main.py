import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.routes import (
    accounts,
    administration,
    auth,
    custom_reports,
    fiscal,
    imports,
    journals,
    ledger,
    migration,
    planning,
    reports,
)
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Disposition",
        "X-Report-Run-ID",
        "X-Report-Digest",
        "X-Correlation-ID",
    ],
)


@app.middleware("http")
async def correlation_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    request.state.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "The requested change violates a data integrity constraint"},
    )


@app.get("/health")
def health():  # type: ignore[no-untyped-def]
    return {"status": "ok"}


for router in (
    auth.router,
    fiscal.router,
    accounts.router,
    journals.router,
    ledger.router,
    planning.router,
    reports.router,
    custom_reports.router,
    administration.router,
    imports.router,
    migration.router,
):
    app.include_router(router, prefix="/api/v1")
