from abc import ABC, abstractmethod


class DocumentTextExtractor(ABC):
    """
    Porta para extracao de texto de documentos PDF.
    O FinanceService depende desta interface, nao da implementacao concreta.
    """

    @abstractmethod
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Extrai texto de um documento PDF.

        Args:
            file_bytes: Conteudo binario do arquivo.
            filename: Nome original do arquivo (incluindo extensao).

        Returns:
            Texto bruto extraido do documento.

        Raises:
            ExtractionTimeoutError: Se o processamento nao concluir dentro do timeout.
            ExtractionError: Se houver erro na extracao.
        """
        ...
