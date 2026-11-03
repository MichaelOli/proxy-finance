from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import tomllib

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from loguru import logger

from app.api.v1.endpoints.banks import router as banks_router
from app.api.v1.endpoints.finance import router as finance_router
from app.core.config import settings
from app.core.exceptions import (
    BankCodeMismatchError,
    BankNotIdentifiedError,
    ExtractionError,
    ParsingError,
    UnsupportedBankError,
)

# ---------------------------------------------------------------------------
# Metadata lida do pyproject.toml em runtime
# ---------------------------------------------------------------------------

def _find_pyproject(start: Path) -> Path:
    for p in [start, *start.parents]:
        candidate = p / "pyproject.toml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("pyproject.toml não encontrado")


_pyproject = _find_pyproject(Path(__file__).resolve())
_meta = tomllib.loads(_pyproject.read_bytes().decode("utf-8"))

APP_NAME = _meta["project"]["name"]
APP_VERSION = _meta["project"]["version"]
APP_DESCRIPTION = _meta["project"].get("description", "")

ROOT_PATH = settings.root_path

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Tratamento global de exceções de domínio
# ---------------------------------------------------------------------------

@app.exception_handler(UnsupportedBankError)
async def unsupported_bank_handler(_request, exc: UnsupportedBankError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "code": "UNSUPPORTED_BANK", "message": str(exc)},
    )


@app.exception_handler(BankNotIdentifiedError)
async def bank_not_identified_handler(_request, exc: BankNotIdentifiedError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "code": "BANK_NOT_IDENTIFIED", "message": str(exc)},
    )


@app.exception_handler(BankCodeMismatchError)
async def bank_code_mismatch_handler(_request, exc: BankCodeMismatchError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "code": "BANK_CODE_MISMATCH", "message": str(exc)},
    )


@app.exception_handler(ParsingError)
async def parsing_error_handler(_request, exc: ParsingError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "code": "PARSING_ERROR", "message": str(exc)},
    )


@app.exception_handler(ExtractionError)
async def extraction_error_handler(_request, exc: ExtractionError):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "code": "OCR_ERROR", "message": str(exc)},
    )

# ---------------------------------------------------------------------------
# Autenticacao via API Key
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> None:
    """Valida API Key quando autenticacao esta habilitada."""
    if not settings.api_key_enabled:
        return
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API Key invalida ou ausente")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

public = APIRouter()

_auth_dep = Depends(verify_api_key) if settings.api_key_enabled else Depends(lambda: None)
protected = APIRouter(dependencies=[_auth_dep])

if not settings.api_key_enabled:
    logger.warning("API_KEY_ENABLED=false - autenticacao DESABILITADA (modo desenvolvimento).")


# --- Rotas públicas ---------------------------------------------------------

@public.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": APP_VERSION}


@public.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=f"{ROOT_PATH}/openapi.json",
        title=f"{APP_NAME} - Swagger UI",
    )


@public.get("/openapi.json", include_in_schema=False)
async def get_openapi():
    return JSONResponse(app.openapi())


# --- Rotas protegidas -------------------------------------------------------


protected.include_router(finance_router, prefix="/finance", tags=["finance"])
protected.include_router(banks_router, prefix="/banks", tags=["banks"])


# --- Monta tudo sob ROOT_PATH -----------------------------------------------

app.include_router(public, prefix=ROOT_PATH)
app.include_router(protected, prefix=ROOT_PATH)

logger.info("Aplicação '{}' v{} iniciada. ROOT_PATH={}", APP_NAME, APP_VERSION, ROOT_PATH)
