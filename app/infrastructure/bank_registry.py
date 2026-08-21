"""
Registro central de bancos do sistema.

O código COMPE (3 dígitos, ex: "001", "102") é o identificador operacional
em todo o sistema — é amplamente conhecido: aparece em boletos, extratos e
aplicativos bancários.

O campo `ispb` é opcional e existe apenas para bancos já registrados.

Como adicionar um novo banco:
  1. Inclua uma entrada em _BANK_REGISTRY com nome e codigo (COMPE).
  2. Se houver parser implementado, adicione também em parser_factory.py.
     Nenhum outro arquivo precisa ser tocado (OCP).
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BankEntry:
    nome: str
    codigo: str              # Código COMPE — identificador operacional (3 dígitos, zero-padded)
    ispb: Optional[str] = field(default=None)  # Referência BACEN/SPB — opcional, não usado internamente


_BANK_REGISTRY: list[BankEntry] = [
    BankEntry("Banco do Brasil",         codigo="001", ispb="00000000"),
    BankEntry("Caixa Econômica Federal", codigo="104", ispb="00360305"),
    BankEntry("Bradesco",                codigo="237", ispb="60746948"),
    BankEntry("Santander",               codigo="033", ispb="33172537"),
    BankEntry("Itaú Unibanco",           codigo="341", ispb="60701190"),
    BankEntry("XP Investimentos",        codigo="102", ispb="02332886"),
    BankEntry("BTG Pactual",             codigo="208", ispb="30306294"),
    BankEntry("Nubank",                  codigo="260", ispb="18236120"),
    BankEntry("Inter",                   codigo="077", ispb="00416968"),
    BankEntry("Rico Investimentos",      codigo="381", ispb="92874270"),
    BankEntry("Banco Safra",             codigo="422"),
    BankEntry("BTG Pactual",             codigo="208"),
]

# Índices para lookup rápido O(1)
_INDEX_BY_CODIGO: dict[str, BankEntry] = {b.codigo: b for b in _BANK_REGISTRY}
_INDEX_BY_ISPB: dict[str, BankEntry] = {b.ispb: b for b in _BANK_REGISTRY if b.ispb is not None}


def get_bank_registry() -> list[BankEntry]:
    """Retorna a lista completa de bancos registrados."""
    return _BANK_REGISTRY


def get_bank_by_codigo(codigo: str) -> BankEntry | None:
    """
    Busca um banco pelo código COMPE.
    Aceita "1", "01" ou "001" — normaliza para 3 dígitos com zero-padding.
    Retorna None se não encontrado.
    """
    normalized = codigo.strip().zfill(3)
    return _INDEX_BY_CODIGO.get(normalized)


def get_bank_by_ispb(ispb: str) -> BankEntry | None:
    """Busca um banco pelo ISPB (8 dígitos). Retorna None se não encontrado."""
    return _INDEX_BY_ISPB.get(ispb)
