# EasyStuffs

Ferramentas simples para o dia-a-dia.

## Atualizador de Imagens

Executavel Windows que copia/atualiza as imagens da pasta `update` para todas as outras pastas e subpastas, no mesmo sitio onde o `.exe` e colocado.

**Download:** [dist/ImageUpdater.exe](dist/ImageUpdater.exe)

### Como usar

1. Coloque `ImageUpdater.exe` na pasta raiz do trabalho.
2. Crie uma pasta chamada `update` nessa mesma raiz.
3. Ponha la as imagens novas (`jpg`, `jpeg`, `png`, `gif`, `bmp`, `webp`, `tif`, `svg`, `ico`, ...).
4. As restantes pastas (e subpastas) sao os destinos.
5. Duplo clique em `ImageUpdater.exe`.

```
pasta-raiz/
  ImageUpdater.exe
  update/
    logo.png          <- origem (imagens novas)
    produto.jpg
    atualizacao-imagens.log
  loja-a/
    logo.png          <- atualizado (mesmo nome)
    produtos/         <- tambem recebe as imagens
  loja-b/
    ...
```

Quando abrir o programa pode escolher:

1. **Copiar/atualizar em todas as pastas e subpastas** — as imagens da pasta `update` passam a existir em cada pasta de destino; se ja existir um ficheiro com o mesmo nome, e substituido.
2. **Atualizar apenas as que ja existem** — so substitui ficheiros com o mesmo nome; nao cria imagens novas nas pastas.

A pasta `update`, a raiz junto ao `.exe`, pastas ocultas e `.git` nao sao alteradas. Ficheiros que ja estejam iguais sao ignorados. Fica um log em `update/atualizacao-imagens.log`.

### Linha de comandos

```bat
ImageUpdater.exe
ImageUpdater.exe -yes
ImageUpdater.exe -mode all -yes
ImageUpdater.exe -mode existing -yes
ImageUpdater.exe -root "D:\trabalho\fotos" -mode all -yes
```

### Compilar o .exe

Na pasta `image-updater`:

```bash
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o ../dist/ImageUpdater.exe .
```

O CI do GitHub tambem gera o `ImageUpdater.exe` em cada push (artefacto da action **Build ImageUpdater**).
