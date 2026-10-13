from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def ok(data=None, status_code: int = status.HTTP_200_OK, message: str | None = None) -> dict:
    """Ο φάκελος κάθε επιτυχημένης απάντησης. Το status_code πρέπει να είναι ίδιο με του decorator."""
    return {"status_code": status_code, "success": True, "message": message, "data": data}


def error(status_code: int, message: str, data=None, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"status_code": status_code, "success": False, "message": message, "data": data},
                        status_code, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return error(exc.status_code, str(exc.detail), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Μόνο πεδίο και μήνυμα: το "input" του Pydantic θα επέστρεφε πίσω ό,τι στάλθηκε, ακόμα και κωδικούς.
        fields = [{"field": ".".join(str(part) for part in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return error(status.HTTP_422_UNPROCESSABLE_CONTENT, "Μη έγκυρα δεδομένα", fields)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Εσωτερικό σφάλμα")
