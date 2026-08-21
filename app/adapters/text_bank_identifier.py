"""
Handler 2 da cadeia de identificação: extrai o texto completo do PDF
e verifica keywords mapeadas por código COMPE.

Lê todas as páginas do documento pois alguns bancos incluem o nome institucional
apenas em notas de rodapé ou páginas posteriores à capa.

Lógica de scoring:
  - required: ao menos 1 deve estar no texto; se nenhuma bater, o banco é descartado
  - optional: reforçam a identificação, mas sozinhas não bastam
  - min_score: mínimo de (required_hits + optional_hits) para confirmar

Para adicionar um novo banco (somente após ter parser implementado):
  1. Inclua uma entrada no _KEYWORD_MAP com BankKeywordConfig usando o código COMPE
  2. Use required apenas para termos inequivocamente exclusivos do banco
  3. Coloque termos genéricos em optional
"""
from dataclasses import dataclass, field
from typing import Optional

import pdfplumber
from loguru import logger

from app.domain.ports.bank_identifier import BankIdentifierHandler, IdentificationContext


@dataclass
class BankKeywordConfig:
    required: list[str]           # ao menos 1 deve bater; 0 hits = banco descartado
    optional: list[str] = field(default_factory=list)  # reforçam, mas sozinhas não bastam
    min_score: int = 1            # mínimo de (required_hits + optional_hits) para confirmar


# Mapa código COMPE → configuração de keywords.
# Contém apenas bancos com parser implementado (OCP: novos bancos = nova entrada aqui).
_KEYWORD_MAP: dict[str, BankKeywordConfig] = {
    "001": BankKeywordConfig(
        required=["Banco do Brasil", "BB DTVM", "BB Investimentos"],
        optional=["https://www.bb.com.br/"],
    ),
    "102": BankKeywordConfig(
        required=["XP Investimentos", "XP INVESTIMENTOS", "XP Inc"],
        optional=["https://www.xp.com.br/"],
    ),
    "422": BankKeywordConfig(
        required=["Banco Safra", "Central de Atendimento Safra"],
        optional=["safra.com.br", "Safra Asset"],
    ),
    "208": BankKeywordConfig(
        required=["BTG Pactual", "BANCO BTG PACTUAL"],
        optional=["banking.btgpactual.com", "0800-772-2827"],
    ),
    "341": BankKeywordConfig(
        # Ao menos 1 required deve bater (min_score=1 padrão).
        # Termos exclusivos do Itaú Private — nunca aparecem em extratos de outras instituições.
        required=["ITAUVEST", "Itau Flexprev", "ITAÚ PRIVATE"],
        optional=["LIG-DI ITAU", "LIG-IPCA ITAU", "LCA-DI ITAU"],
    ),
    
}


class TextKeywordHandler(BankIdentifierHandler):
    """
    Tenta identificar o banco pelo texto completo do PDF via pdfplumber.

    Para cada banco no mapa:
      1. Verifica se ao menos 1 keyword required está no texto (senão descarta)
      2. Conta hits de optional
      3. Confirma se (required_hits + optional_hits) >= min_score
    """

    def _try_identify(self, context: IdentificationContext) -> Optional[str]:
        try:
            text = self._extract_text(context)
        except Exception as exc:
            logger.warning("TextKeywordHandler: falha ao extrair texto — {}", exc)
            return None

        if not text:
            return None

        context.document_text = text  # disponibiliza para handlers subsequentes

        for codigo, config in _KEYWORD_MAP.items():
            required_hits = [kw for kw in config.required if kw in text]
            if not required_hits:
                continue

            optional_hits = [kw for kw in config.optional if kw in text]
            score = len(required_hits) + len(optional_hits)

            if score >= config.min_score:
                logger.info(
                    "TextKeywordHandler: codigo={} | required={} | optional={} | score={}",
                    codigo,
                    required_hits,
                    optional_hits,
                    score,
                )
                return codigo

        logger.debug(
            "TextKeywordHandler: nenhuma keyword correspondeu. "
            "Trecho extraído (primeiros 500 chars):\n{}",
            text[:500] if text else "(vazio)",
        )
        return None

    @staticmethod
    def _extract_text(context: IdentificationContext) -> str:
        """Extrai o texto completo do PDF (todas as páginas)."""
        if context.document_text is not None:
            return context.document_text

        import io
        with pdfplumber.open(io.BytesIO(context.file_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages_text)
