# Projeto Atena (Consolidado)

Bem-vindo à versão consolidada e refatorada do Projeto Atena. Este guia centraliza as informações para execução, desenvolvimento e manutenção do sistema.

## Arquitetura

O projeto é um aplicativo de desktop híbrido com a seguinte estrutura:

- `/backend`: Aplicação em **Python (FastAPI)** que serve a IA, processa dados e gerencia a automação.
- `/frontend`: Interface de usuário em **React (Vite + TypeScript)**.
- `/desktop`: Wrapper **Tauri** que empacota o frontend em um aplicativo de desktop.
- `/docs`: Documentação geral do projeto.
- `/scripts`: Scripts úteis para automação de tarefas.

---

## 1. Instalação

Execute os passos a seguir em seus respectivos diretórios.

### 1.1. Backend

```bash
cd backend
pip install -r requirements.txt
```

### 1.2. Frontend & Desktop

```bash
cd frontend
npm install

cd ../desktop
npm install
```

---

## 2. Como Executar (Modo de Desenvolvimento)

Para facilitar o desenvolvimento, utilize o script `run_dev.bat` na raiz deste projeto. Ele iniciará o backend e o frontend simultaneamente.

```bash
# Na raiz de Atena_Consolidada
./run_dev.bat
```

O script executará os seguintes comandos em terminais separados:
- **Backend:** `cd backend && uvicorn app.main:app --reload` (assumindo que o entrypoint é `app/main.py`)
- **Frontend:** `cd frontend && npm run dev`

---

## 3. Como "Buildar" a Aplicação Final

Para gerar o executável final do desktop:

```bash
# Na raiz de Atena_Consolidada
./build_app.bat
```
Este script irá primeiro buildar o frontend React e depois o aplicativo Tauri. O resultado estará em `desktop/src-tauri/target/release`.

---

## 4. Como Fazer a Atena Assimilar uma Nova LLM

A troca do modelo de linguagem local é feita através de uma variável de ambiente.

1.  **Obtenha o Modelo:** Baixe um novo modelo de linguagem em formato **GGUF** (como os do Hugging Face).
2.  **Coloque na Pasta:** Salve o arquivo `.gguf` em um local acessível, por exemplo, dentro de `backend/models/`.
3.  **Atualize a Configuração:**
    - Abra o arquivo `.env` que estará localizado dentro da pasta `backend`.
    - Altere a variável `ATENA_LLM_LOCAL_MODEL_PATH` para o caminho completo do novo modelo.

    **Exemplo:**
    ```env
    # .env (dentro da pasta /backend)

    # Apontando para um novo modelo
    ATENA_LLM_LOCAL_MODEL_PATH="C:/path/to/your/new_model.gguf"
    ```

4.  **Reinicie o Backend:** Se o backend estiver rodando, reinicie-o para que ele carregue o novo modelo.
