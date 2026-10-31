@echo off
rem Grava saida.txt na mesma pasta desta batch.
rem Linha 1 = string com 12 caracteres
rem Linha 2 = numero com 17 caracteres
rem Linha 3 = numero com 2 caracteres
rem Uso: criar_txt.bat ABCDEFGHIJKL 12345678901234567 42

if "%~3"=="" (
    echo Uso: %~nx0 ^<12caracteres^> ^<17digitos^> ^<2digitos^>
    exit /b 1
)

> "%~dp0saida.txt" echo %~1
>> "%~dp0saida.txt" echo %~2
>> "%~dp0saida.txt" echo %~3
echo Ficheiro criado: %~dp0saida.txt
