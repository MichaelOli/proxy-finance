# proxy-finance

API FastAPI para parsing estruturado de extratos financeiros em PDF.

## O que faz

1. Recebe um PDF de extrato financeiro via `POST /api/v1/proxy-finance/finance/parse`
2. Identifica o banco automaticamente (keywords no texto ou hash da logo)
3. Valida que o documento corresponde ao banco informado (evita parsings incorretos)
4. Extrai o texto do PDF localmente via `pdfplumber`
5. Aplica parser regex especifico por banco
6. Retorna JSON completamente estruturado com todas as secoes do extrato

## Bancos suportados


| Banco            | Codigo COMPE | Status       |
| ---------------- | ------------ | ------------ |
| Banco do Brasil  | `001`        | Implementado |
| XP Investimentos | `102`        | Implementado |
| BTG Pactual      | `208`        | Implementado |
| Itau Unibanco    | `341`        | Implementado |
| Banco Safra      | `422`        | Implementado |


Todos os bancos conhecidos (mesmo sem parser) estao disponiveis em `GET /api/v1/proxy-finance/banks`.

## Pre-requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) instalado
- Poppler instalado (necessario para identificacao por logo via `pdf2image`)
  - Linux/macOS: `apt install poppler-utils` / `brew install poppler`
  - Windows: `winget install oschwartz10612.Poppler` ou baixar em [https://github.com/oschwartz10612/poppler-windows/releases](https://github.com/oschwartz10612/poppler-windows/releases)



## Instalacao e execucao local

```bash
# 1. Clone e entre na pasta
cd proxy-finance

# 2. Crie o ambiente e instale dependencias
uv sync

# 3. Configure as variaveis de ambiente
cp .env.example .env
# edite .env: POPPLER_PATH (Windows)

# 4. Suba o servidor
uv run uvicorn app.main:app --reload --port 8000
```

Documentacao Swagger: `http://localhost:8001/api/v1/proxy-finance/docs`

Health check: `http://localhost:8001/api/v1/proxy-finance/health`

## Docker

```bash
docker-compose up --build
```



## Estrutura do projeto

```
app/
  main.py                          # FastAPI app, routers, exception handlers
  core/
    config.py                      # Settings (pydantic-settings)
    exceptions.py                  # Excecoes de dominio
  domain/
    models/                        # Pydantic models do JSON de saida
    ports/                         # ABCs: DocumentParser, BankIdentifierHandler
  adapters/
    pdf_text_extractor_gateway.py  # Extracao local de texto via pdfplumber
    text_bank_identifier.py        # Identificacao por keywords no texto
    logo_bank_identifier.py        # Identificacao por perceptual hash da logo
  parsers/
    parser_factory.py              # Factory: codigo COMPE -> Parser
    bb/                            # Parsers do Banco do Brasil (001)
    xp/                            # Parsers da XP Investimentos (102)
    btg/                           # Parsers do BTG Pactual (208)
    itau/                          # Parsers do Itau Unibanco (341)
    safra/                         # Parsers do Banco Safra (422)
  services/
    finance_service.py             # Orquestra identificacao + parsing
    bank_identification_service.py # Cadeia de identificacao
  infrastructure/
    bank_registry.py               # Catalogo central de bancos
    logo_registry.py               # Mapa codigo COMPE -> hash da logo
  api/v1/endpoints/
    finance.py                     # POST /finance/parse
    banks.py                       # GET /banks
tests/
  parsers/                         # Testes unitarios dos parsers
  adapters/                        # Testes dos adapters
  services/                        # Testes dos servicos
docs/
  fluxo-parse-documento.md         # Fluxo detalhado do parsing
  como-escalar-novos-bancos.md     # Guia para adicionar novos bancos
```



## Design patterns


| Pattern                 | Onde                                     | Papel                                      |
| ----------------------- | ---------------------------------------- | ------------------------------------------ |
| Strategy                | `DocumentParser` ABC + parsers por banco | Cada banco implementa seu proprio parser   |
| Factory                 | `ParserFactory`                          | Seleciona o parser pelo codigo COMPE       |
| Chain of Responsibility | Handlers de identificacao                | `BankCodeProvided` -> `Text` -> `Logo`     |
| Adapter                 | `PdfTextExtractorGateway`                | Isola a biblioteca `pdfplumber` do dominio |
| Registry                | `bank_registry.py`, `logo_registry.py`   | Fonte unica de verdade para bancos e logos |
| SRP                     | Sub-modulos por banco                    | Um modulo por secao de documento           |




## Identificacao do banco

O sistema usa duas cadeias de identificacao:

- **Cadeia principal** - `BankCodeProvided` -> `Text` -> `Logo`
- **Cadeia de deteccao** (validacao do hint) - `Text` -> `Logo`

Quando `bank_code` e informado, a **cadeia de deteccao** e executada primeiro para verificar se o documento realmente pertence ao banco informado. Se houver contradicao, a requisicao e rejeitada com `422 BANK_CODE_MISMATCH`.

## Possiveis respostas de erro


| HTTP  | Codigo                | Motivo                                              |
| ----- | --------------------- | --------------------------------------------------- |
| `401` | -                     | API Key invalida (quando autenticacao habilitada)   |
| `422` | `BANK_NOT_IDENTIFIED` | Nenhum handler conseguiu identificar o banco        |
| `422` | `UNSUPPORTED_BANK`    | Banco identificado, mas sem parser implementado     |
| `422` | `BANK_CODE_MISMATCH`  | O `bank_code` informado contradiz o banco detectado |
| `422` | `PARSING_ERROR`       | Parser falhou ao processar o documento              |
| `500` | `OCR_ERROR`           | Falha na leitura do PDF (corrompido ou escaneado)   |




## Testes

```bash
uv run pytest tests/ -v
```



## Como adicionar suporte a um novo banco

Veja `docs/como-escalar-novos-bancos.md` para o guia completo passo a passo.

## Variaveis de ambiente


| Variavel              | Padrao                  | Descricao                    |
| --------------------- | ----------------------- | ---------------------------- |
| `ROOT_PATH`           | `/api/v1/proxy-finance` | Prefixo das rotas            |
| `HTTP_PORT`           | `8001`                  | Porta HTTP                   |
| `LOGO_HASH_THRESHOLD` | `10`                    | Threshold para hash de logo  |
| `POPPLER_PATH`        | ``                      | Caminho do Poppler (Windows) |
| `API_KEY_ENABLED`     | `false`                 | Habilitar autenticacao       |
| `API_KEY`             | ``                      | Chave de API                 |


