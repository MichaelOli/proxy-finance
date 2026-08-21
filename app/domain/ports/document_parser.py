from abc import ABC, abstractmethod

from app.domain.models.portfolio import BasePortfolioData


class DocumentParser(ABC):
    """
    Strategy: cada banco implementa este contrato.
    Recebe o texto bruto extraído pelo OCR e retorna um BasePortfolioData estruturado.
    Cada banco retorna seu próprio subtipo (PortfolioData, XpPortfolioData, etc.).
    """

    @property
    @abstractmethod
    def bank_codigo(self) -> str:
        """Código COMPE do banco que este parser suporta (ex: '001', '102')."""
        ...

    @abstractmethod
    def parse(self, text: str) -> BasePortfolioData:
        """
        Parseia o texto bruto do extrato e retorna o modelo estruturado.

        Args:
            text: Texto bruto extraído do PDF via pdfplumber.

        Returns:
            Subtipo de BasePortfolioData com todas as seções preenchidas.

        Raises:
            ValueError: Se o texto não corresponde ao formato esperado do banco.
        """
        ...
