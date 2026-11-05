# Comparar códigos

Programa Windows (`.exe`) que lê dois códigos de barras com o formato `1#SSSSSSSPPPPPPPPPP` e diz se os números são iguais.

- `1#` é fixo.
- `S` são os 7 dígitos logo a seguir.
- `P` são os 10 dígitos a seguir ao `S`.

O programa compara o `S` de um código com o `S` do outro, e o `P` de um com o `P` do outro. O resultado é **IGUAIS** só quando os dois números coincidem. Se um deles mudar, o resultado é **DIFERENTES** e a linha desse número mostra os dois valores.

Os zeros à esquerda contam. `0000001` e `0000002` são números diferentes.

## Como usar

**No ecrã** — duplo clique em `comparar-codigos.exe` e leia os dois códigos. O leitor de códigos envia Enter no fim de cada leitura. Uma linha vazia fecha o programa. Depois de cada par pode ler outros dois.

**Na linha de comandos**

```bat
comparar-codigos.exe 1#12345671234567890 1#12345671234567890
```

O programa termina com código 0 quando os números são iguais, 2 quando diferem e 1 quando um código não tem o formato certo.

## Exemplo

```text
Codigo 1: 1#12345671234567890
Codigo 2: 1#12345679999999999
Numero S: 1234567 igual a 1234567
Numero P: 1234567890 diferente de 9999999999
Resultado: DIFERENTES
```

## Compilar (opcional)

Precisa de [Go](https://go.dev/). Nesta pasta:

```bat
go test
go build -ldflags="-s -w" -o comparar-codigos.exe
```

Para gerar o `.exe` a partir de Linux ou macOS:

```sh
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o comparar-codigos.exe
```
