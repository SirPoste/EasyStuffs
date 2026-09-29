@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Cria saida.txt com dois numeros recebidos na chamada:
rem   linha 1 = input1 (17 digitos)
rem   linha 2 = input2 (2 digitos)
rem
rem Uso:
rem   criar_txt.bat 12345678901234567 42

if "%~1"=="" goto :uso
if "%~2"=="" goto :uso
if not "%~3"=="" goto :uso

set "INPUT1=%~1"
set "INPUT2=%~2"

echo(!INPUT1!| findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$" >nul
if errorlevel 1 (
    echo Erro: o 1.o argumento tem de ser um numero com exactamente 17 digitos.
    exit /b 1
)

echo(!INPUT2!| findstr /r "^[0-9][0-9]$" >nul
if errorlevel 1 (
    echo Erro: o 2.o argumento tem de ser um numero com exactamente 2 digitos.
    exit /b 1
)

set "FICHEIRO=saida.txt"
(
    echo(!INPUT1!
    echo(!INPUT2!
) > "!FICHEIRO!"

echo Ficheiro criado: !FICHEIRO!
endlocal
exit /b 0

:uso
echo Uso: %~nx0 ^<17digitos^> ^<2digitos^>
echo Exemplo: %~nx0 12345678901234567 42
exit /b 1
