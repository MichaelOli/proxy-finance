"""
ParserFactory — seleciona o DocumentParser correto com base no código COMPE do banco.

Para registrar um novo banco:
  1. Importe o parser: from app.parsers.xyz.xyz_parser import XYZParser
  2. Adicione ao _REGISTRY: "codigo_compe": XYZParser

Nenhum outro arquivo precisa ser modificado (OCP).
"""
from app.core.exceptions import UnsupportedBankError
from app.domain.ports.document_parser import DocumentParser
from app.parsers.bb.bb_parser import BBParser
from app.parsers.btg.btg_parser import BtgParser
from app.parsers.itau.itau_parser import ItauParser
from app.parsers.safra.safra_parser import SafraParser
from app.parsers.xp.xp_parser import XpParser

_REGISTRY: dict[str, type[DocumentParser]] = {
    "001": BBParser,    # Banco do Brasil
    "102": XpParser,    # XP Investimentos
    "208": BtgParser,   # BTG Pactual
    "341": ItauParser,  # Itaú Unibanco
    "422": SafraParser, # Banco Safra
}


class ParserFactory:
    @staticmethod
    def get_parser(codigo: str) -> DocumentParser:
        """
        Retorna uma instância do parser registrado para o código COMPE fornecido.

        Raises:
            UnsupportedBankError: Se o código não tiver parser implementado.
        """
        cls = _REGISTRY.get(codigo)
        if cls is None:
            raise UnsupportedBankError(codigo)
        return cls()

    @staticmethod
    def supported_banks() -> list[str]:
        """Retorna lista de códigos COMPE com parser registrado."""
        return list(_REGISTRY.keys())
