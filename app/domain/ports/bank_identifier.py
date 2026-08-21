from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IdentificationContext:
    """
    Contexto compartilhado entre os handlers da cadeia de identificação.
    Cada handler pode enriquecer o contexto para o próximo.
    """
    file_bytes: bytes
    filename: str
    bank_codigo_hint: Optional[str] = None  # código COMPE fornecido pelo cliente (pode ser None)
    document_text: Optional[str] = None  # populado pelo TextKeywordHandler (texto completo do PDF)
    first_page_image_bytes: Optional[bytes] = None  # populado pelo LogoHashHandler se necessário


class BankIdentifierHandler(ABC):
    """
    Chain of Responsibility: cada handler tenta identificar o banco.
    Se não conseguir, passa para o próximo handler da cadeia.
    """

    _next: Optional["BankIdentifierHandler"] = None

    def set_next(self, handler: "BankIdentifierHandler") -> "BankIdentifierHandler":
        self._next = handler
        return handler

    def identify(self, context: IdentificationContext) -> Optional[str]:
        """
        Tenta identificar o banco. Retorna o código COMPE se identificado,
        ou chama o próximo handler se não conseguir.

        Returns:
            Código COMPE como string, ou None se nenhum handler identificar.
        """
        result = self._try_identify(context)
        if result is not None:
            return result
        if self._next is not None:
            return self._next.identify(context)
        return None

    @abstractmethod
    def _try_identify(self, context: IdentificationContext) -> Optional[str]:
        """Lógica de identificação específica deste handler. Retorna código COMPE ou None."""
        ...
