# criar-txt

Batch do Windows que grava os argumentos, um por linha, em `saida.txt` na mesma pasta do script.

O tamanho de cada valor é validado noutro processo, antes desta chamada. Se faltar algum argumento, o script mostra o uso e não cria o ficheiro.

## Como usar

```bat
criar_txt.bat 12345678901234567 42 7
```

O ficheiro `saida.txt` fica assim:

```text
12345678901234567
42
7
```
