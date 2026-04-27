@echo off
echo ============================================
echo    POLARIS IA — Servidor Local
echo ============================================
echo.

:: Ir a la carpeta del servidor
cd /d "%~dp0"

:: Verificar si el entorno virtual existe
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/3] Entorno virtual encontrado
)

:: Activar entorno virtual
echo [2/3] Activando entorno virtual...
call venv\Scripts\activate.bat

:: Instalar dependencias si no están
echo [3/3] Verificando dependencias...
pip install -r requirements.txt -q

:: Arrancar el servidor
echo.
echo ============================================
echo    Polaris IA arrancando en:
echo    http://localhost:8000
echo    Docs: http://localhost:8000/docs
echo ============================================
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
