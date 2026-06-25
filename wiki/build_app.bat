@echo off
REM Script para buildar a aplicação desktop final da Atena.

REM Muda para o diretório onde o script está localizado para garantir que os caminhos funcionem
cd /d "%~dp0"

echo "Iniciando build do Frontend (React)..."
cd frontend
npm run build

if %errorlevel% neq 0 (
    echo "Erro no build do frontend! Abortando."
    exit /b %errorlevel%
)

echo "Frontend buildado com sucesso. Iniciando build do Desktop (Tauri)..."
cd ../desktop
npm run build

if %errorlevel% neq 0 (
    echo "Erro no build do Tauri! Abortando."
    exit /b %errorlevel%
)

echo "Build da aplicação concluído com sucesso!"
echo "O executável pode ser encontrado em: desktop\src-tauri\target\release"
pause