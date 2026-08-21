"""
Handler 3 da cadeia de identificação: renderiza a 1ª página como imagem,
recorta a região específica onde cada banco posiciona seu logo, e compara
o perceptual hash contra o registro em logo_registry.py.

Cada banco pode ter o logo em posição diferente na página (topo, rodapé, etc.).
As coordenadas de recorte são configuradas por código COMPE em LogoConfig.

Usado quando a identificação por texto falha (ex: PDF sem nome do banco como texto).
"""
import io
from typing import Optional

from loguru import logger

from app.domain.ports.bank_identifier import BankIdentifierHandler, IdentificationContext
from app.infrastructure.logo_registry import get_logo_registry, get_threshold


class LogoHashHandler(BankIdentifierHandler):
    """
    Identifica o banco pelo hash do logo.
    Cada banco tem sua própria região de recorte definida em LogoConfig.
    """

    def _try_identify(self, context: IdentificationContext) -> Optional[str]:
        try:
            import imagehash
            from PIL import Image
        except ImportError:
            logger.warning("LogoHashHandler: dependências 'imagehash' ou 'Pillow' não instaladas — handler ignorado.")
            return None

        try:
            image_bytes = self._render_first_page(context)
        except Exception as exc:
            logger.warning("LogoHashHandler: falha ao renderizar 1ª página — {}", exc)
            return None

        try:
            img = Image.open(io.BytesIO(image_bytes))
            w, h = img.size
        except Exception as exc:
            logger.warning("LogoHashHandler: falha ao abrir imagem — {}", exc)
            return None

        threshold = get_threshold()
        for codigo, config in get_logo_registry().items():
            try:
                crop_box = (
                    int(w * config.crop_left),
                    int(h * config.crop_top),
                    int(w * config.crop_right),
                    int(h * config.crop_bottom),
                )
                logo_region = img.crop(crop_box)
                doc_hash = imagehash.phash(logo_region)
                ref_hash = imagehash.hex_to_hash(config.hash)
                distance = doc_hash - ref_hash
                if distance <= threshold:
                    logger.info(
                        "LogoHashHandler: banco identificado — codigo={} (distância={})",
                        codigo,
                        distance,
                    )
                    return codigo
            except Exception as exc:
                logger.warning("LogoHashHandler: erro ao comparar hash para codigo={} — {}", codigo, exc)

        logger.debug("LogoHashHandler: nenhum hash correspondeu.")
        return None

    @staticmethod
    def _render_first_page(context: IdentificationContext) -> bytes:
        if context.first_page_image_bytes is not None:
            return context.first_page_image_bytes

        from pdf2image import convert_from_bytes

        from app.core.config import settings
        poppler_path = settings.poppler_path or None  # None = usa PATH do sistema

        pages = convert_from_bytes(
            context.file_bytes,
            dpi=150,
            first_page=1,
            last_page=1,
            poppler_path=poppler_path,
        )
        if not pages:
            raise ValueError("pdf2image não retornou páginas.")

        buf = io.BytesIO()
        pages[0].save(buf, format="PNG")
        image_bytes = buf.getvalue()
        context.first_page_image_bytes = image_bytes
        return image_bytes
