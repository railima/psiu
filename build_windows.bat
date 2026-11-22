@echo off
rem Gera dist\Psiu.exe (requer Python 3.12+ instalado: winget install Python.Python.3.12)
cd /d "%~dp0"

py -3 -m venv .venv || goto :error
.venv\Scripts\python -m pip install --upgrade pip || goto :error
.venv\Scripts\python -m pip install pywebview pyinstaller PyAudioWPatch numpy || goto :error
.venv\Scripts\pyinstaller --noconfirm --clean psiu.spec || goto :error

echo.
echo Pronto: %cd%\dist\Psiu.exe
pause
exit /b 0

:error
echo.
echo Falhou. Veja a mensagem acima.
pause
exit /b 1
