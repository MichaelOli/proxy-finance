"""
Endpoint POST /finance/parse

Recebe um PDF de extrato financeiro, identifica o banco automaticamente,
extrai o texto localmente e retorna JSON estruturado.
"""
from typing import Optional

from loguru import logger

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.services.finance_service import FinanceService


router = APIRouter()

_service = FinanceService()


@router.post(
    "/parse",
    summary="Parsear extrato financeiro",
    description=(
        "Recebe um PDF de extrato financeiro, identifica o banco automaticamente "
        "(por codigo COMPE, keywords no texto ou hash da logo), extrai o texto "
        "localmente via pdfplumber e retorna JSON estruturado com todas as secoes."
    ),
    response_description="JSON estruturado com todas as secoes do extrato financeiro.",
    responses={
        200: {"description": "Parsing concluido com sucesso."},
        422: {"description": "Banco nao identificado ou nao suportado."},
        500: {"description": "Erro na leitura do PDF."},
    },
)
async def parse_finance_document(
    file: UploadFile = File(..., description="PDF do extrato financeiro."),
    bank_code: Optional[str] = Form(
        default=None,
        description=(
            "Código COMPE do banco (3 dígitos). Se informado, pula a identificação automática. "
            "Exemplos: '001' para Banco do Brasil, '102' para XP Investimentos, '341' para Itaú. "
            "Consulte GET /v1/banks para a lista completa."
        ),
    ),
) -> JSONResponse:
    logger.info(
        "parse_finance_document: arquivo='{}', bank_code={}",
        file.filename,
        bank_code,
    )

    file_bytes = await file.read()

    portfolio = await _service.parse_document(
        file_bytes=file_bytes,
        filename=file.filename or "upload.pdf",
        bank_codigo_hint=bank_code,
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "bank": portfolio.banco.model_dump(),
            "parsed_data": portfolio.model_dump(),
        },
    )
