class UnsupportedBankError(Exception):
    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__(f"Banco com código '{codigo}' não possui parser implementado.")


class BankNotIdentifiedError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Não foi possível identificar o banco pelo documento enviado. "
            "Informe o parâmetro 'bank_code' para forçar o parser."
        )


class BankCodeMismatchError(Exception):
    """
    Levantada quando o código informado pelo cliente (bank_code) contradiz
    o banco identificado pelo conteúdo do documento.
    """
    def __init__(self, provided: str, detected: str) -> None:
        self.provided = provided
        self.detected = detected
        super().__init__(
            f"O código '{provided}' informado não corresponde ao banco identificado "
            f"no documento (código '{detected}'). Verifique o parâmetro 'bank_code'."
        )


class ParsingError(Exception):
    """
    Levantada quando o parser falha ao processar o documento.
    Geralmente indica que o banco informado não corresponde ao documento enviado.
    """
    def __init__(self, codigo: str, detail: str) -> None:
        self.codigo = codigo
        super().__init__(
            f"Falha ao analisar o documento com o parser do banco '{codigo}'. "
            f"Verifique se o banco informado corresponde ao documento enviado. "
            f"Detalhe: {detail}"
        )


class OcrProcessingError(Exception):
    def __init__(self, task_id: str, message: str) -> None:
        self.task_id = task_id
        super().__init__(f"Erro na extração de texto do PDF. task_id={task_id} — {message}")
