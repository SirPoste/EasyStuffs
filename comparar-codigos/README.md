# Comparar códigos

Programa Windows que lê dois códigos de barras no formato `1#SSSSSSSPPPPPPPPPP` e compara o número **S**.

- `1#` é fixo.
- `S` são os 7 dígitos logo a seguir. É este número que tem de ser igual.
- `P` são os 10 dígitos a seguir ao `S`. Não entra na comparação.

Os zeros à esquerda contam. `0000001` e `0000002` são números diferentes.

## Na página

Duplo clique em `comparar-codigos.exe`. Não abre uma janela de consola: o browser abre direto na página.

1. Leia o primeiro código. O leitor envia Enter e o cursor passa ao segundo campo.
2. Leia o segundo código.
3. A página mostra **IGUAIS** ou **DIFERENTES**.

O logotipo dos quatro anéis fica no topo da página. **Nova leitura** limpa os dois campos. **Sair** fecha o programa. Fechar só o separador do browser deixa o programa a correr; outro duplo clique volta a abrir a página.

## Na linha de comandos

```bat
comparar-codigos.exe 1#12345671234567890 1#12345679999999999
```

O `S` destes dois códigos é `1234567` nos dois, por isso o resultado é igual mesmo que o `P` mude. O programa termina com código 0 quando o `S` é igual, 2 quando é diferente e 1 quando um código não tem o formato certo.

```text
Codigo 1: 1#12345671234567890
Codigo 2: 1#12345679999999999
Numero S: 1234567 igual a 1234567
Resultado: IGUAIS
```

## Compilar (opcional)

Precisa de [Go](https://go.dev/). Nesta pasta:

```bat
go test
go build -ldflags="-s -w -H windowsgui" -o comparar-codigos.exe
```

Para gerar o `.exe` a partir de Linux ou macOS:

```sh
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w -H windowsgui" -o comparar-codigos.exe
```
