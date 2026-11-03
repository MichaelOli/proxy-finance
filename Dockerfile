# Etapa 1 — Base Python com UV
FROM python:3.12-slim AS base

# Define o diretório de trabalho
WORKDIR /app

# Dependências de sistema: poppler (pdf2image) + curl + gcc (libs nativas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala o UV e adiciona ao PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.local/bin:/root/.cargo/bin:$PATH" && \
    ln -sf /root/.cargo/bin/uv /usr/local/bin/uv

# Copia os arquivos de dependência primeiro (para aproveitar cache)
COPY pyproject.toml uv.lock* ./

# Garante que o uv esteja acessível
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Instala dependências do projeto
RUN uv sync --no-dev

# Copia o restante do código
COPY . .

# Expõe a porta do FastAPI
EXPOSE 8000

# Comando de execução — ajustável conforme seu entrypoint
ENV UVICORN_WORKERS=4

# --proxy-headers e forwarded-allow-ips para rodar atrás de proxy
CMD uv run uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --workers ${UVICORN_WORKERS} \
  --proxy-headers --forwarded-allow-ips="*"