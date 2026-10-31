@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Levantamento de imagens
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 comparar_imagens.py
  if errorlevel 1 pause
  goto :eof
)
where python >nul 2>&1
if %errorlevel%==0 (
  python comparar_imagens.py
  if errorlevel 1 pause
  goto :eof
)
echo Nao foi encontrado o Python 3.
echo Instale Python 3 em https://www.python.org/downloads/
echo Na instalacao, marque "Add python.exe to PATH".
pause
