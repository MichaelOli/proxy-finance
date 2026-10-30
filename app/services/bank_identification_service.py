"""
Monta e executa a cadeia de identificação do banco (Chain of Responsibility).

Duas cadeias são mantidas:

  Cadeia principal (identify):
    1. BankCodeProvidedHandler — código COMPE fornecido diretamente pelo cliente (sem I/O)
    2. TextKeywordHandler      — keywords no texto via pdfplumber
    3. LogoHashHandler         — hash perceptual do logo via pdf2image

  Cadeia de detecção (validação de hint):
    1. TextKeywordHandler      — mesmo handler, sem o BankCodeProvidedHandler
    2. LogoHashHandler         — executa se texto retornar None

Quando o cliente fornece bank_codigo_hint, a cadeia de detecção é executada antes
da cadeia principal. Se ela detectar um código diferente do hint, o sistema rejeita
a requisição com BankCodeMismatchError (422) — cobrindo bancos com texto E bancos
identificáveis apenas por logo (como XP).

O IdentificationContext faz cache de document_text e first_page_image_bytes, então
o I/O realizado na validação é reutilizado pela cadeia principal.
"""
from typing import Optional

from loguru import logger

from app.adapters.logo_bank_identifier import LogoHashHandler
from app.adapters.text_bank_identifier import TextKeywordHandler
from app.core.exceptions import BankCodeMismatchError, BankNotIdentifiedError
from app.domain.ports.bank_identifier import BankIdentifierHandler, IdentificationContext


class BankCodeProvidedHandler(BankIdentifierHandler):
    """
    Handler 1: se o cliente já informou o código COMPE, retorna imediatamente sem I/O.
    """

    def _try_identify(self, context: IdentificationContext) -> Optional[str]:
        if context.bank_codigo_hint:
            logger.info(
                "BankCodeProvidedHandler: codigo={} fornecido pelo cliente.",
                context.bank_codigo_hint,
            )
            return context.bank_codigo_hint
        return None


def build_identification_chain() -> BankIdentifierHandler:
    """
    Cadeia principal: BankCodeProvided -> Text -> Logo.
    Usada para todo fluxo de identificação normal.
    """
    code_handler = BankCodeProvidedHandler()
    text_handler = TextKeywordHandler()
    logo_handler = LogoHashHandler()

    code_handler.set_next(text_handler).set_next(logo_handler)
    return code_handler


def build_detection_chain() -> BankIdentifierHandler:
    """
    Cadeia de detecção pura: Text -> Logo (sem BankCodeProvidedHandler).
    Usada para validar o hint fornecido pelo cliente — detecta o banco real
    pelo conteúdo do documento, independente do que o cliente informou.
    """
    text_handler = TextKeywordHandler()
    logo_handler = LogoHashHandler()

    text_handler.set_next(logo_handler)
    return text_handler


class BankIdentificationService:
    """
    Ponto de entrada para a identificação do banco.
    Monta a cadeia e executa, lançando BankNotIdentifiedError se nenhum handler resolver.
    """

    def __init__(self) -> None:
        self._chain: BankIdentifierHandler = build_identification_chain()
        self._detection_chain: BankIdentifierHandler = build_detection_chain()

    def identify(
        self,
        file_bytes: bytes,
        filename: str,
        bank_codigo_hint: Optional[str] = None,
    ) -> str:
        """
        Identifica o banco e retorna o código COMPE.

        Quando bank_codigo_hint é fornecido, a cadeia de detecção completa
        (texto + logo) é executada para verificar se o documento corresponde
        ao banco informado. Se a detecção automática encontrar um banco diferente
        do hint, BankCodeMismatchError é informado.

        Se a detecção automática não conseguir identificar o banco (ex: banco novo
        ainda sem keywords/logo registrados), o hint é confiado sem erro.

        Raises:
            BankNotIdentifiedError: Se nenhum handler da cadeia conseguiu identificar.
            BankCodeMismatchError: Se o hint contradiz o banco detectado no documento.
        """
        context = IdentificationContext(
            file_bytes=file_bytes,
            filename=filename,
            bank_codigo_hint=bank_codigo_hint,
        )

        if bank_codigo_hint:
            self._validate_hint(context, bank_codigo_hint)

        codigo = self._chain.identify(context)
        if codigo is None:
            raise BankNotIdentifiedError()
        return codigo

    def _validate_hint(
        self,
        context: IdentificationContext,
        hint: str,
    ) -> None:
        """
        Executa a cadeia de detecção pura (texto + logo) e compara com o hint.

        - Detecção retorna um código diferente do hint -> BankCodeMismatchError
        - Detecção retorna None (banco não reconhecido) -> hint confiado, sem erro
        - Detecção retorna o mesmo código do hint -> OK, prossegue normalmente

        O contexto já acumula o cache de texto e imagem durante esta validação,
        então a cadeia principal não refaz nenhum I/O.
        """
        detected = self._detection_chain.identify(context)

        if detected is None:
            logger.debug(
                "BankIdentificationService: detecção automática não reconheceu o banco "
                "— hint={} confiado sem validação adicional.",
                hint,
            )
            return

        if detected != hint:
            logger.warning(
                "BankIdentificationService: hint={} contradiz detecção automática (detectado={}).",
                hint,
                detected,
            )
            raise BankCodeMismatchError(provided=hint, detected=detected)

        logger.debug(
            "BankIdentificationService: hint={} confirmado pela detecção automática.",
            hint,
        )
