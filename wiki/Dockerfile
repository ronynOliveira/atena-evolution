# ===================================================
# DOCKERFILE SIMPLIFICADO - FOCO NA EXECUÇÃO
# Sem a cópia da memória FAISS por enquanto.
# ===================================================

# Estágio 1: Instalar dependências
FROM python:3.11-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir --prefix="/install" --force-reinstall --ignore-installed -r requirements.txt
RUN pip list

# Estágio 2: Construir a imagem final
FROM python:3.11-slim
WORKDIR /atena_app

# Copia as dependências já instaladas do estágio anterior
COPY --from=builder /install /usr/local

# Copia APENAS o código-fonte da aplicação
COPY ./src ./app

EXPOSE 8000
# O comando para iniciar a aplicação, apontando para o arquivo e objeto corretos.
CMD ["uvicorn", "app.atena_servidor_unified:app", "--host", "0.0.0.0", "--port", "8000"]