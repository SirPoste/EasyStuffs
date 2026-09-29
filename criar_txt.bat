@echo off
rem Linha 1 = primeiro argumento, linha 2 = segundo argumento.
rem Uso: criar_txt.bat 12345678901234567 42

if "%~2"=="" (
    echo Uso: %~nx0 ^<input1^> ^<input2^>
    exit /b 1
)

> saida.txt echo %~1
>> saida.txt echo %~2
echo Ficheiro criado: saida.txt
