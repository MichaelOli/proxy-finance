"""
Registro de hashes perceptuais das logos dos bancos.

Cada banco pode ter seu logo em uma posição diferente na página.
O LogoConfig define tanto o hash quanto as coordenadas de recorte
(como fração da largura/altura da imagem renderizada).

Como adicionar o hash de um novo banco:
  1. Renderize a 1ª página do PDF de amostra:
       from pdf2image import convert_from_bytes
       pages = convert_from_bytes(open("extrato.pdf","rb").read(), dpi=150, first_page=1, last_page=1)
  2. Descubra onde o logo aparece na página (inspecione pages[0])
  3. Recorte a região do logo usando as proporções corretas
  4. Execute:
       import imagehash
       crop = pages[0].crop((left, top, right, bottom))
       print(str(imagehash.phash(crop)))
  5. Adicione uma entrada em _LOGO_REGISTRY com o hash e as proporções de recorte.

O threshold padrão (LOGO_HASH_THRESHOLD=10) tolera até 10 bits de diferença,
o que cobre variações de compressão JPEG e escala. Reduza para maior precisão.
"""
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class LogoConfig:
    """Configuração de identificação visual por hash de logo."""
    hash: str
    # Proporções do recorte (fração de 0.0 a 1.0 sobre largura/altura da imagem)
    crop_left: float = 0.0
    crop_top: float = 0.0
    crop_right: float = 0.20
    crop_bottom: float = 0.12


# Mapa código COMPE → configuração de logo.
# hash gerado com imagehash.phash a partir do PDF de amostra em DPI 150.
_LOGO_REGISTRY: dict[str, LogoConfig] = {
    # Banco do Brasil — logo no canto superior-esquerdo (padrão)
    # "001": LogoConfig(hash="<hash_bb>", crop_left=0.0, crop_top=0.0, crop_right=0.20, crop_bottom=0.12),

    # XP Investimentos — logo "xp unique" no RODAPÉ inferior-esquerdo
    "102": LogoConfig(
        hash="bcc1c336383867c7",
        crop_left=0.0,
        crop_top=0.92,
        crop_right=0.20,
        crop_bottom=1.0,
    ),

    # Banco Safra — brasão + nome "Safra" no canto superior-direito
    "422": LogoConfig(
        hash="ea95954ab5915a2d",
        crop_left=0.72,
        crop_top=0.0,
        crop_right=1.0,
        crop_bottom=0.09,
    ),

    # BTG Pactual — logotipo "btg pactual" no canto superior-direito
    "208": LogoConfig(
        hash="ed926d92496c936c",
        crop_left=0.72,
        crop_top=0.0,
        crop_right=1.0,
        crop_bottom=0.10,
    ),

    # Itaú Unibanco — barra laranja horizontal no topo de todas as páginas
    # (a capa com logo textual está ausente da amostra; a barra laranja aparece
    #  consistentemente em todas as páginas disponíveis no mesmo y=0.10-0.13).
    "341": LogoConfig(
        hash="aad52a2ad52ad5d4",
        crop_left=0.0,
        crop_top=0.10,
        crop_right=1.0,
        crop_bottom=0.13,
    ),
}

THRESHOLD: int = settings.logo_hash_threshold


def get_logo_registry() -> dict[str, LogoConfig]:
    return _LOGO_REGISTRY


def get_threshold() -> int:
    return THRESHOLD
