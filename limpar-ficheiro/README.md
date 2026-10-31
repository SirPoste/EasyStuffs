# limpar-ficheiro

Programa Windows (`.exe`) que recebe um ficheiro como argumento — `.dat` ou qualquer outro — e **esvazia o conteúdo**, sem apagar o ficheiro. O ficheiro continua no mesmo sítio, mas fica com 0 bytes.

O executável desta pasta é `limpar-ficheiro.exe`.

## Como usar

**Opção 1 — arrastar o ficheiro**

Arraste o `.dat` (ou outro ficheiro) para cima de `limpar-ficheiro.exe`.

**Opção 2 — linha de comandos**

```bat
limpar-ficheiro.exe save.dat
limpar-ficheiro.exe C:\pasta\jogo.dat notas.txt
```

## O que faz e o que não faz

- Remove todo o conteúdo do ficheiro (fica vazio).
- Não apaga o ficheiro da pasta.
- Não cria ficheiros novos: se o caminho não existir, mostra erro.
- Recusa pastas e atalhos/symlinks.

**Atenção:** a operação é permanente. Não há recuperação do conteúdo pelo programa.

## Compilar (opcional)

Precisa de [Go](https://go.dev/). Nesta pasta:

```bat
go test
go build -ldflags="-s -w" -o limpar-ficheiro.exe
```

Para gerar o `.exe` a partir de Linux ou macOS:

```sh
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o limpar-ficheiro.exe
```
