@echo off
cd /d "%~dp0"
echo ==========================================
echo PPGCA - SOLICITACAO DE VEICULOS
ECHO ==========================================
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 goto falha
  py -3 iniciar.py
) else (
  python -m pip install -r requirements.txt
  if errorlevel 1 goto falha
  python iniciar.py
)
pause
exit /b
:falha
echo Nao foi possivel instalar. Confira sua conexao e instalacao do Python.
pause
