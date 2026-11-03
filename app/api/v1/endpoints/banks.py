"""
Endpoint GET /v1/banks

Lista os bancos suportados pelo serviço com nome, código COMPE e status de suporte.
Permite que o frontend exiba um select com os bancos disponíveis e envie o
código correto ao chamar /v1/finance/parse.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.infrastructure.bank_registry import get_bank_registry
from app.parsers.parser_factory import ParserFactory

router = APIRouter()


class BankInfo(BaseModel):
    nome: str
    codigo: str   # Código COMPE (3 dígitos, ex: "001", "102")
    suportado: bool


@router.get(
    "",
    summary="Listar bancos suportados",
    description=(
        "Retorna a lista de bancos conhecidos pelo serviço. "
        "Use o campo `codigo` como valor do parâmetro `bank_code` ao chamar "
        "POST /v1/finance/parse para forçar o parser de um banco específico. "
        "Bancos com `suportado: false` ainda não possuem parser implementado — "
        "o serviço tentará identificá-los automaticamente pelo documento, mas não "
        "garantirá o parsing estruturado."
    ),
    response_model=list[BankInfo],
)
def list_banks() -> list[BankInfo]:
    supported_codigos = set(ParserFactory.supported_banks())

    return [
        BankInfo(
            nome=bank.nome,
            codigo=bank.codigo,
            suportado=bank.codigo in supported_codigos,
        )
        for bank in get_bank_registry()
    ]
