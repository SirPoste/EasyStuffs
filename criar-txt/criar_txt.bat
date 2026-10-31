@echo off
rem Grava saida.txt na mesma pasta desta batch.
rem Linha 1 = primeiro argumento, linha 2 = segundo argumento, linha 3 = terceiro argumento.
rem Uso: criar_txt.bat 12345678901234567 42 7

if "%~3"=="" (
    echo Uso: %~nx0 ^<input1^> ^<input2^> ^<input3^>
    exit /b 1
)

> "%~dp0saida.txt" echo %~1
>> "%~dp0saida.txt" echo %~2
>> "%~dp0saida.txt" echo %~3
echo Ficheiro criado: %~dp0saida.txt
