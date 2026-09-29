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

call :validar "!INPUT1!" 17 "primeiro argumento"
if errorlevel 1 exit /b 1
call :validar "!INPUT2!" 2 "segundo argumento"
if errorlevel 1 exit /b 1

set "FICHEIRO=saida.txt"
> "!FICHEIRO!" echo !INPUT1!
>> "!FICHEIRO!" echo !INPUT2!

echo Ficheiro criado: !FICHEIRO!
endlocal
exit /b 0

:validar
set "VALOR=%~1"
set "ESPERADO=%~2"
set "RESTO=!VALOR!"
set /a CONT=0

:validar_loop
if "!RESTO!"=="" goto :validar_fim
set "CH=!RESTO:~0,1!"
set "RESTO=!RESTO:~1!"
set "DIGITO=0"
for %%D in (0 1 2 3 4 5 6 7 8 9) do if "!CH!"=="%%D" set "DIGITO=1"
if "!DIGITO!"=="0" goto :validar_falha
set /a CONT+=1
if !CONT! gtr %ESPERADO% goto :validar_falha
goto :validar_loop

:validar_fim
if not !CONT! equ %ESPERADO% goto :validar_falha
exit /b 0

:validar_falha
echo Erro: o %~3 tem de ser um numero com exactamente %~2 digitos.
exit /b 1

:uso
echo Uso: %~nx0 ^<17digitos^> ^<2digitos^>
echo Exemplo: %~nx0 12345678901234567 42
exit /b 1
