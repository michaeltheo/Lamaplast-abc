from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.responses import error, register_error_handlers
from app.routers import audit, auth, health, items, lookups, users
from app.schemas.response import ApiResponse, FieldError

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ABC Costing System for Lamaplast",
    responses={422: {"model": ApiResponse[list[FieldError]], "description": "Μη έγκυρα δεδομένα"}},
)

register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_foreign_origins(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        own = f"{request.url.scheme}://{request.url.netloc}"
        if origin != own and origin not in settings.cors_origins:
            return error(status.HTTP_403_FORBIDDEN, "Μη επιτρεπτό origin")
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(lookups.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(items.router)
