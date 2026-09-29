@echo off
rem Grava saida.txt na mesma pasta desta batch.
rem Linha 1 = primeiro argumento, linha 2 = segundo argumento.
rem Uso: criar_txt.bat 12345678901234567 42

if "%~2"=="" (
    echo Uso: %~nx0 ^<input1^> ^<input2^>
    exit /b 1
)

> "%~dp0saida.txt" echo %~1
>> "%~dp0saida.txt" echo %~2
echo Ficheiro criado: %~dp0saida.txt
