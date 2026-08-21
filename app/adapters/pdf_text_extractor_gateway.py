"""
Adapter que extrai texto do PDFs, sem dependencias de rede.

Implementa DocumentTextExtractor (Adapter Pattern + DIP):
  - O dominio depende apenas da porta DocumentTextExtractor (circulo interno)
  - Este adapter vive no circulo externo e traduz a interface do pdfplumber
    para o contrato esperado pelo FinanceService
"""
import io

import pdfplumber
from loguru import logger

from app.core.exceptions import ExtractionError
from app.domain.ports.document_text_extractor import DocumentTextExtractor


class PdfTextExtractorGateway(DocumentTextExtractor):
    """
    Adapter: extrai texto de PDFs localmente via pdfplumber.
    Implementacao de DocumentTextExtractor.
    """

    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Abre o PDF em memória e extrai o texto de todas as páginas concatenadas.

        Args:
            file_bytes: Conteúdo binário do PDF.
            filename: Nome original do arquivo (usado apenas para logging).

        Returns:
            Texto bruto extraído de todas as páginas, separado por '\\n'.

        Raises:
            ExtractionError: Se o PDF nao puder ser lido ou estiver vazio.
        """
        logger.info("PdfTextExtractorGateway: extraindo texto de '{}'.", filename)
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            raise ExtractionError(
                task_id="local",
                message=f"Falha ao ler o PDF '{filename}': {exc}",
            ) from exc

        text = "\n".join(pages)

        if not text.strip():
            raise ExtractionError(
                task_id="local",
                message=f"Nenhum texto extraido do PDF '{filename}'. O arquivo pode ser uma imagem escaneada sem camada de texto.",
            )

        logger.info(
            "PdfTextExtractorGateway: '{}' processado — {} páginas, {} caracteres.",
            filename,
            len(pages),
            len(text),
        )
        return text
