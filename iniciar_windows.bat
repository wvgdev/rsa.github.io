@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 goto erro
python app.py
pause
exit /b
:erro
echo Instale Python e marque Add Python to PATH. Verifique sua internet.
pause
