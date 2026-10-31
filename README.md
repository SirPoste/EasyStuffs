# EasyStuffs

Pequenos programas utilitarios.

## limpar-ficheiro

Programa Windows (`.exe`) que recebe um ficheiro como argumento — `.dat` ou qualquer outro — e **esvazia o conteudo**, sem apagar o ficheiro. O ficheiro continua no mesmo sitio, mas fica com 0 bytes.

### Como usar

**Opcao 1 — arrastar o ficheiro**

Arraste o `.dat` (ou outro ficheiro) para cima de `limpar-ficheiro.exe`.

**Opcao 2 — linha de comandos**

```bat
limpar-ficheiro.exe save.dat
limpar-ficheiro.exe C:\pasta\jogo.dat notas.txt
```

O executavel esta em `limpar-ficheiro/limpar-ficheiro.exe`.

### O que faz e o que nao faz

- Remove todo o conteudo do ficheiro (fica vazio).
- Nao apaga o ficheiro da pasta.
- Nao cria ficheiros novos: se o caminho nao existir, mostra erro.
- Recusa pastas e atalhos/symlinks.

**Atencao:** a operacao e permanente. Nao ha recuperacao do conteudo pelo programa.

### Compilar (opcional)

Precisa de [Go](https://go.dev/). Na pasta `limpar-ficheiro`:

```bat
go test
go build -ldflags="-s -w" -o limpar-ficheiro.exe
```

Para gerar o `.exe` a partir de Linux/macOS:

```sh
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o limpar-ficheiro.exe
```
