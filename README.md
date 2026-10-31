# EasyStuffs

## Levantamento de imagens

Compara a pasta de referência **C8PA** com uma pasta de análise e mostra que imagens estão em falta ou com conteúdo diferente. As imagens diferentes podem ser copiadas para uma terceira pasta.

Não é preciso instalar bibliotecas. Basta o Python 3.

### No Windows

1. Instale o Python 3 em [python.org](https://www.python.org/downloads/) e marque **Add python.exe to PATH**.
2. Faça duplo clique em `iniciar.bat`.
3. Na página que abre, indique a pasta C8PA, a pasta de análise e a pasta de destino.
4. Carregue em **Comparar**.
5. Veja as miniaturas em falta, com conteúdo diferente, ambíguas ou só na análise.
6. Carregue em **Copiar diferenças**.

Deixe a janela do programa aberta enquanto usa a página. Para sair, feche essa janela ou prima Ctrl+C.

O botão **Escolher…** abre o explorador de pastas quando o Python inclui o Tk. Se não abrir, cole o caminho: no Explorador de Ficheiros, clique na barra de endereço, copie e cole.

### O que é copiado

A referência e a análise não são alteradas. Na pasta de destino aparecem:

- `em_falta` — imagens da C8PA que não estão na análise
- `conteudo_diferente` — as duas versões, quando o nome coincide e o ficheiro é diferente
- `ambiguos` — o mesmo nome aparece mais do que uma vez e não houve correspondência automática
- `so_na_analise` — só se marcar essa opção
- `relatorio.csv` e `resumo.txt` — o levantamento completo (o CSV abre no Excel)

### Como a comparação funciona

- **Pelo nome do ficheiro** (predefinição): a subpasta pode ser diferente.
- **Pelo caminho relativo**: a subpasta também tem de coincidir.
- Maiúsculas e minúsculas são ignoradas, a menos que desmarque a opção.
- **Diferente** significa que os bytes do ficheiro não são iguais. Não é uma comparação visual: uma imagem regravada com outra qualidade conta como diferente.

### Noutro sistema

```bash
python3 comparar_imagens.py
```
