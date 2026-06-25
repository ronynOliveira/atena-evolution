@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM ATENA - Assistente Simbiótica - Script de Desenvolvimento Robusto
REM ============================================================================
REM Sistema inteligente de inicialização com monitoramento e recuperação
REM ============================================================================

title ATENA - Sistema de Desenvolvimento

REM Configurações
set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\atena_startup_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=%LOG_FILE: =0%"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "MAX_RETRIES=3"
set "HEALTH_CHECK_INTERVAL=30"

REM Cores para output (usando caracteres especiais)
set "COLOR_GREEN=[92m"
set "COLOR_RED=[91m"
set "COLOR_YELLOW=[93m"
set "COLOR_BLUE=[94m"
set "COLOR_RESET=[0m"

REM Muda para o diretório do script
cd /d "%~dp0"

REM Cria diretório de logs se não existir
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM ============================================================================
REM FUNÇÕES AUXILIARES
REM ============================================================================

call :LogMessage "INFO" "=== ATENA - Iniciando Sistema de Desenvolvimento ==="
call :LogMessage "INFO" "Timestamp: %date% %time%"

REM Verifica se Python está instalado
call :LogMessage "INFO" "Verificando dependências..."
python --version >nul 2>&1
if errorlevel 1 (
    call :LogMessage "ERROR" "Python não encontrado! Instale Python 3.8+ antes de continuar."
    echo %COLOR_RED%[ERRO] Python não encontrado!%COLOR_RESET%
    pause
    exit /b 1
)

REM Verifica se Node.js está instalado
node --version >nul 2>&1
if errorlevel 1 (
    call :LogMessage "ERROR" "Node.js não encontrado! Instale Node.js antes de continuar."
    echo %COLOR_RED%[ERRO] Node.js não encontrado!%COLOR_RESET%
    pause
    exit /b 1
)

echo %COLOR_GREEN%[OK] Dependências verificadas%COLOR_RESET%
call :LogMessage "INFO" "Todas as dependências verificadas com sucesso"

REM ============================================================================
REM VERIFICAÇÃO DE PORTAS
REM ============================================================================

call :LogMessage "INFO" "Verificando disponibilidade de portas..."
echo %COLOR_BLUE%[INFO] Verificando portas...%COLOR_RESET%

netstat -ano | findstr ":%BACKEND_PORT%" >nul
if not errorlevel 1 (
    call :LogMessage "WARNING" "Porta %BACKEND_PORT% já está em uso. Tentando liberar..."
    echo %COLOR_YELLOW%[AVISO] Porta %BACKEND_PORT% em uso - tentando liberar...%COLOR_RESET%
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 >nul
)

netstat -ano | findstr ":%FRONTEND_PORT%" >nul
if not errorlevel 1 (
    call :LogMessage "WARNING" "Porta %FRONTEND_PORT% já está em uso. Tentando liberar..."
    echo %COLOR_YELLOW%[AVISO] Porta %FRONTEND_PORT% em uso - tentando liberar...%COLOR_RESET%
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 >nul
)

echo %COLOR_GREEN%[OK] Portas disponíveis%COLOR_RESET%

REM ============================================================================
REM VERIFICAÇÃO DE AMBIENTE VIRTUAL (BACKEND)
REM ============================================================================

call :LogMessage "INFO" "Verificando ambiente virtual Python..."
if not exist "backend\venv" (
    echo %COLOR_YELLOW%[AVISO] Ambiente virtual não encontrado. Criando...%COLOR_RESET%
    call :LogMessage "INFO" "Criando ambiente virtual Python..."
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    cd ..
    echo %COLOR_GREEN%[OK] Ambiente virtual criado%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[OK] Ambiente virtual encontrado%COLOR_RESET%
)

REM ============================================================================
REM VERIFICAÇÃO DE DEPENDÊNCIAS NODE
REM ============================================================================

call :LogMessage "INFO" "Verificando dependências Node.js..."
if not exist "frontend\node_modules" (
    echo %COLOR_YELLOW%[AVISO] Dependências Node não encontradas. Instalando...%COLOR_RESET%
    call :LogMessage "INFO" "Instalando dependências Node.js..."
    cd frontend
    call npm install
    cd ..
    echo %COLOR_GREEN%[OK] Dependências instaladas%COLOR_RESET%
) else (
    echo %COLOR_GREEN%[OK] Dependências Node encontradas%COLOR_RESET%
)

REM ============================================================================
REM INICIALIZAÇÃO DOS SERVIÇOS
REM ============================================================================

echo.
echo %COLOR_BLUE%========================================%COLOR_RESET%
echo %COLOR_BLUE%  INICIANDO ATENA - MODO DESENVOLVIMENTO%COLOR_RESET%
echo %COLOR_BLUE%========================================%COLOR_RESET%
echo.

REM Inicia Backend com retry
call :LogMessage "INFO" "Iniciando Backend (FastAPI) na porta %BACKEND_PORT%..."
echo %COLOR_BLUE%[BACKEND] Iniciando servidor FastAPI...%COLOR_RESET%
start "ATENA - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port %BACKEND_PORT% --host 0.0.0.0"

timeout /t 3 >nul

REM Inicia Frontend
call :LogMessage "INFO" "Iniciando Frontend (React) na porta %FRONTEND_PORT%..."
echo %COLOR_BLUE%[FRONTEND] Iniciando servidor React...%COLOR_RESET%
start "ATENA - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 >nul

REM ============================================================================
REM MONITORAMENTO E HEALTH CHECK
REM ============================================================================

echo.
echo %COLOR_GREEN%========================================%COLOR_RESET%
echo %COLOR_GREEN%  ATENA INICIADA COM SUCESSO!%COLOR_RESET%
echo %COLOR_GREEN%========================================%COLOR_RESET%
echo.
echo %COLOR_BLUE%Backend:%COLOR_RESET%  http://localhost:%BACKEND_PORT%
echo %COLOR_BLUE%Frontend:%COLOR_RESET% http://localhost:%FRONTEND_PORT%
echo %COLOR_BLUE%API Docs:%COLOR_RESET% http://localhost:%BACKEND_PORT%/docs
echo.
echo %COLOR_YELLOW%Pressione Ctrl+C para encerrar todos os serviços%COLOR_RESET%
echo.

call :LogMessage "INFO" "Sistema iniciado com sucesso"
call :LogMessage "INFO" "Backend: http://localhost:%BACKEND_PORT%"
call :LogMessage "INFO" "Frontend: http://localhost:%FRONTEND_PORT%"

REM Cria script de monitoramento
call :CreateMonitorScript

REM Inicia monitoramento em background
start "ATENA - Monitor" /MIN cmd /c "%~dp0atena_monitor.bat"

REM Mantém a janela principal aberta
echo %COLOR_BLUE%[INFO] Sistema de monitoramento ativo%COLOR_RESET%
echo %COLOR_BLUE%[INFO] Logs salvos em: %LOG_DIR%%COLOR_RESET%
echo.

:WaitLoop
timeout /t %HEALTH_CHECK_INTERVAL% >nul
call :HealthCheck
goto WaitLoop

REM ============================================================================
REM FUNÇÃO: LogMessage
REM ============================================================================
:LogMessage
set "LEVEL=%~1"
set "MESSAGE=%~2"
echo [%date% %time%] [%LEVEL%] %MESSAGE% >> "%LOG_FILE%"
goto :eof

REM ============================================================================
REM FUNÇÃO: HealthCheck
REM ============================================================================
:HealthCheck
REM Verifica se o backend está rodando
tasklist /FI "WINDOWTITLE eq ATENA - Backend" 2>nul | find /i "cmd.exe" >nul
if errorlevel 1 (
    call :LogMessage "ERROR" "Backend não está respondendo! Tentando reiniciar..."
    echo %COLOR_RED%[ERRO] Backend caiu! Reiniciando...%COLOR_RESET%
    start "ATENA - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port %BACKEND_PORT% --host 0.0.0.0"
)

REM Verifica se o frontend está rodando
tasklist /FI "WINDOWTITLE eq ATENA - Frontend" 2>nul | find /i "cmd.exe" >nul
if errorlevel 1 (
    call :LogMessage "ERROR" "Frontend não está respondendo! Tentando reiniciar..."
    echo %COLOR_RED%[ERRO] Frontend caiu! Reiniciando...%COLOR_RESET%
    start "ATENA - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
)
goto :eof

REM ============================================================================
REM FUNÇÃO: CreateMonitorScript
REM ============================================================================
:CreateMonitorScript
(
echo @echo off
echo setlocal enabledelayedexpansion
echo title ATENA - Monitor de Saúde
echo.
echo :MonitorLoop
echo timeout /t 30 ^>nul
echo.
echo REM Verifica processos
echo tasklist /FI "WINDOWTITLE eq ATENA - Backend" 2^>nul ^| find /i "cmd.exe" ^>nul
echo if errorlevel 1 ^(
echo     echo [%%date%% %%time%%] Backend caiu - Reiniciando... ^>^> "%LOG_DIR%\monitor.log"
echo     start "ATENA - Backend" cmd /k "cd /d "%~dp0backend" ^&^& call venv\Scripts\activate.bat ^&^& python -m uvicorn app.main:app --reload --port %BACKEND_PORT% --host 0.0.0.0"
echo ^)
echo.
echo tasklist /FI "WINDOWTITLE eq ATENA - Frontend" 2^>nul ^| find /i "cmd.exe" ^>nul
echo if errorlevel 1 ^(
echo     echo [%%date%% %%time%%] Frontend caiu - Reiniciando... ^>^> "%LOG_DIR%\monitor.log"
echo     start "ATENA - Frontend" cmd /k "cd /d "%~dp0frontend" ^&^& npm run dev"
echo ^)
echo.
echo goto MonitorLoop
) > "%~dp0atena_monitor.bat"
goto :eof