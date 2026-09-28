"""Levantamento de imagens entre a pasta de referência (C8PA) e uma pasta de análise.

Abra no Windows com iniciar.bat, ou execute:

    python comparar_imagens.py

O programa abre uma página local. Não instala dependências e não altera
as pastas comparadas. As cópias vão apenas para a pasta de destino.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
import webbrowser
import zlib
from collections import defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePath, PurePosixPath
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

IMAGE_EXTENSIONS = frozenset({
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".ico",
    ".jfif",
    ".jpe",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
})

SKIP_DIRS = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    "$RECYCLE.BIN",
    "System Volume Information",
})

ESTADOS = ("em_falta", "diferente", "ambiguo", "erro", "so_analise", "igual")
ORDER = {estado: indice for indice, estado in enumerate(ESTADOS)}

DEFAULT_INCLUDE = {
    "em_falta": True,
    "diferente": True,
    "ambiguo": True,
    "so_analise": False,
    "erro": True,
}

NOTA_FALTA = "Existe na referência e não aparece na análise."
NOTA_EXTRA = "Existe na análise e não aparece na referência."
NOTA_IGUAL = "O nome e o conteúdo coincidem."
NOTA_DIF_TAM = "O nome corresponde, mas o tamanho do ficheiro é diferente."
NOTA_DIF_HASH = "O nome corresponde, mas o conteúdo do ficheiro é diferente."
NOTA_AMBIGUO = (
    "Há várias imagens com esta correspondência. "
    "Não juntei nenhuma automaticamente, para não misturar ficheiros diferentes."
)

ROTULOS_ESTADO = {
    "em_falta": "em falta",
    "diferente": "conteúdo diferente",
    "ambiguo": "ambíguo",
    "erro": "erro de leitura",
    "so_analise": "só na análise",
    "igual": "igual",
}

BASE_DIR = Path(__file__).resolve().parent
PAGE_PATH = BASE_DIR / "pagina.html"
CONFIG_PATH = BASE_DIR / "ultimas_pastas.json"
EXAMPLE_DIR = BASE_DIR / "exemplo"

mimetypes.add_type("image/heic", ".heic")
mimetypes.add_type("image/heif", ".heif")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/jpeg", ".jfif")
mimetypes.add_type("image/jpeg", ".jpe")


class Cancelado(Exception):
    pass


class NaoEncontrado(Exception):
    pass


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def extensions_label() -> str:
    return ", ".join(sorted(IMAGE_EXTENSIONS))


def solid_png(largura: int, altura: int, rgb: tuple[int, int, int]) -> bytes:
    if largura < 1 or altura < 1:
        raise ValueError("Dimensão inválida.")
    if any(canal < 0 or canal > 255 for canal in rgb):
        raise ValueError("Cor inválida.")

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct_pack(len(data)) + tag + data + struct_pack(crc)

    raw = b"".join(b"\x00" + bytes(rgb) * largura for _ in range(altura))
    ihdr = (
        struct_pack(largura)
        + struct_pack(altura)
        + bytes((8, 2, 0, 0, 0))
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def struct_pack(valor: int) -> bytes:
    return valor.to_bytes(4, "big", signed=False)


def write_png(caminho: Path, largura: int, altura: int, rgb: tuple[int, int, int]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(solid_png(largura, altura, rgb))


def create_example(raiz: Path) -> dict:
    raiz = Path(raiz)
    referencia = raiz / "C8PA"
    analise = raiz / "analise"
    destino = raiz / "destino"
    vermelho = solid_png(320, 200, (190, 48, 42))
    azul = solid_png(320, 200, (36, 86, 176))
    azul_diferente = solid_png(320, 200, (36, 86, 210))
    verde = solid_png(320, 200, (32, 130, 78))
    laranja = solid_png(320, 200, (214, 122, 28))
    cinza = solid_png(320, 200, (128, 128, 128))
    branco = solid_png(320, 200, (245, 245, 245))
    preto = solid_png(320, 200, (20, 20, 20))
    castanho = solid_png(320, 200, (90, 70, 50))
    magenta = solid_png(320, 200, (160, 40, 120))

    def gravar(caminho: Path, conteudo: bytes) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo)

    gravar(referencia / "pecas" / "parafuso.png", vermelho)
    gravar(analise / "pecas" / "parafuso.png", vermelho)
    gravar(referencia / "pecas" / "porca.png", azul)
    gravar(analise / "linha" / "porca.png", azul_diferente)
    gravar(referencia / "pecas" / "anilha.png", verde)
    gravar(referencia / "pecas" / "cavilha_ção.png", magenta)
    gravar(analise / "extra" / "etiqueta.png", laranja)
    gravar(referencia / "tampa.JPG", cinza)
    gravar(analise / "sub" / "tampa.jpg", cinza)
    gravar(referencia / "dup" / "a" / "peca.png", branco)
    gravar(referencia / "dup" / "b" / "peca.png", preto)
    gravar(analise / "peca.png", branco)
    gravar(referencia / "mesmo" / "anel.png", castanho)
    gravar(analise / "mesmo" / "anel.png", castanho)
    (referencia / "notas.txt").parent.mkdir(parents=True, exist_ok=True)
    (referencia / "notas.txt").write_text("ignorar este ficheiro\n", encoding="utf-8")
    (analise / "notas.txt").write_text("ignorar este ficheiro\n", encoding="utf-8")
    destino.mkdir(parents=True, exist_ok=True)
    return {
        "referencia": str(referencia.resolve()),
        "analise": str(analise.resolve()),
        "destino": str(destino.resolve()),
    }


def _check_cancel(cancelar: Optional[Callable[[], bool]]) -> None:
    if cancelar and cancelar():
        raise Cancelado()


def strip_path_text(valor: object) -> str:
    return str(valor or "").strip().strip('"').strip("'").strip()


def require_directory(valor: object, rotulo: str) -> Path:
    texto = strip_path_text(valor)
    if not texto:
        raise ValueError(f"Indique a pasta de {rotulo}.")
    pasta = Path(texto).expanduser().resolve()
    if not pasta.exists():
        raise ValueError(f"Não encontrei a pasta de {rotulo}: {pasta}")
    if not pasta.is_dir():
        raise ValueError(f"O caminho de {rotulo} não é uma pasta: {pasta}")
    try:
        os.listdir(pasta)
    except OSError as exc:
        detalhe = exc.strerror or exc
        raise ValueError(f"Não consigo ler a pasta de {rotulo}: {pasta} ({detalhe})") from exc
    return pasta


def list_images(root: Path, progresso=None, fase: str = "referencia", cancelar=None):
    root = root.resolve()
    found = []
    avisos = []

    def onerror(err: OSError) -> None:
        avisos.append(
            f"Não consegui entrar numa pasta: {err.filename} ({err.strerror or err})"
        )

    rotulo = "referência" if fase == "referencia" else "análise"
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=onerror):
        _check_cancel(cancelar)
        dirnames[:] = sorted(
            (nome for nome in dirnames if nome not in SKIP_DIRS),
            key=str.casefold,
        )
        for nome in sorted(filenames, key=str.casefold):
            caminho = Path(dirpath) / nome
            if caminho.suffix.casefold() not in IMAGE_EXTENSIONS:
                continue
            try:
                if caminho.is_symlink() or not caminho.is_file():
                    continue
                tamanho = caminho.stat().st_size
            except OSError as exc:
                avisos.append(
                    f"Não consegui ler {caminho} ({exc.strerror or exc})"
                )
                continue
            found.append({
                "nome": caminho.name,
                "rel": caminho.relative_to(root).as_posix(),
                "abs": str(caminho),
                "size": tamanho,
            })
            if progresso and (len(found) == 1 or len(found) % 50 == 0):
                progresso(
                    fase,
                    len(found),
                    0,
                    f"A ler a pasta de {rotulo}… {len(found)} imagens",
                )
    if progresso:
        progresso(
            fase,
            len(found),
            len(found),
            f"A ler a pasta de {rotulo}… {len(found)} imagens",
        )
    return found, avisos


def match_key(ficheiro: dict, modo: str, ignorar_maiusculas: bool, ignorar_extensao: bool) -> str:
    if modo == "relativo":
        chave = ficheiro["rel"]
        if ignorar_extensao:
            chave = str(PurePosixPath(chave).with_suffix(""))
    elif modo == "nome":
        chave = ficheiro["nome"]
        if ignorar_extensao:
            chave = PurePath(ficheiro["nome"]).stem
    else:
        raise ValueError("Escolha comparar pelo nome do ficheiro ou pelo caminho relativo.")
    if ignorar_maiusculas:
        chave = chave.casefold()
    return chave


def file_hash(caminho: str, cancelar: Optional[Callable[[], bool]] = None) -> str:
    digest = hashlib.sha256()
    with open(caminho, "rb") as handle:
        while True:
            _check_cancel(cancelar)
            bloco = handle.read(1024 * 1024)
            if not bloco:
                break
            digest.update(bloco)
    return digest.hexdigest()


def public_file(ficheiro: dict, digest: str = "") -> dict:
    return {
        "nome": ficheiro["nome"],
        "rel": ficheiro["rel"],
        "abs": ficheiro["abs"],
        "size": ficheiro["size"],
        "hash": digest,
    }


def make_item(estado: str, chave: str, referencias: list, analises: list, nota: str) -> dict:
    if referencias:
        nome = referencias[0]["nome"]
    else:
        nome = analises[0]["nome"]
    return {
        "estado": estado,
        "nome": nome,
        "chave": chave,
        "nota": nota,
        "referencias": referencias,
        "analises": analises,
    }


def compare_pair(chave: str, referencia: dict, analise: dict, hasher, cancelar) -> dict:
    try:
        if referencia["size"] != analise["size"]:
            return make_item(
                "diferente",
                chave,
                [public_file(referencia)],
                [public_file(analise)],
                NOTA_DIF_TAM,
            )
        digest_ref = hasher(referencia["abs"], cancelar)
        digest_ana = hasher(analise["abs"], cancelar)
    except Cancelado:
        raise
    except OSError as exc:
        return make_item(
            "erro",
            chave,
            [public_file(referencia)],
            [public_file(analise)],
            f"Não foi possível ler um dos ficheiros ({exc.strerror or exc}).",
        )
    if digest_ref == digest_ana:
        return make_item(
            "igual",
            chave,
            [public_file(referencia, digest_ref)],
            [public_file(analise, digest_ana)],
            NOTA_IGUAL,
        )
    return make_item(
        "diferente",
        chave,
        [public_file(referencia, digest_ref)],
        [public_file(analise, digest_ana)],
        NOTA_DIF_HASH,
    )


def pair_items(ref_files, ana_files, modo, ignorar_maiusculas, ignorar_extensao, hasher, cancelar, progresso):
    grupos_ref = defaultdict(list)
    grupos_ana = defaultdict(list)
    for ficheiro in ref_files:
        grupos_ref[match_key(ficheiro, modo, ignorar_maiusculas, ignorar_extensao)].append(ficheiro)
    for ficheiro in ana_files:
        grupos_ana[match_key(ficheiro, modo, ignorar_maiusculas, ignorar_extensao)].append(ficheiro)

    itens = []
    pares = []
    for chave in sorted(set(grupos_ref) | set(grupos_ana), key=str.casefold):
        refs = grupos_ref.get(chave, [])
        anas = grupos_ana.get(chave, [])
        if len(refs) == 1 and len(anas) == 1:
            pares.append((chave, refs[0], anas[0]))
            continue
        if refs and not anas:
            nota = NOTA_FALTA
            if len(refs) > 1:
                nota += " Há outros ficheiros com a mesma correspondência na referência."
            for ficheiro in refs:
                itens.append(make_item("em_falta", chave, [public_file(ficheiro)], [], nota))
            continue
        if anas and not refs:
            nota = NOTA_EXTRA
            if len(anas) > 1:
                nota += " Há outros ficheiros com a mesma correspondência na análise."
            for ficheiro in anas:
                itens.append(make_item("so_analise", chave, [], [public_file(ficheiro)], nota))
            continue
        itens.append(make_item(
            "ambiguo",
            chave,
            [public_file(ficheiro) for ficheiro in refs],
            [public_file(ficheiro) for ficheiro in anas],
            NOTA_AMBIGUO,
        ))

    total = len(pares)
    for indice, (chave, referencia, analise) in enumerate(pares, start=1):
        _check_cancel(cancelar)
        if progresso:
            progresso("comparar", indice, total, f"A verificar o conteúdo… {indice} de {total}")
        itens.append(compare_pair(chave, referencia, analise, hasher, cancelar))

    itens.sort(key=lambda item: (ORDER.get(item["estado"], 9), item["nome"].casefold(), item["chave"].casefold()))
    for numero, item in enumerate(itens, start=1):
        item["id"] = f"i{numero}"
    return itens


def count_totals(itens: list, referencias: int, analises: int) -> dict:
    totais = {estado: 0 for estado in ESTADOS}
    ref_em_ambiguos = 0
    for item in itens:
        totais[item["estado"]] = totais.get(item["estado"], 0) + 1
        if item["estado"] == "ambiguo":
            ref_em_ambiguos += len(item["referencias"])
    totais["referencia"] = referencias
    totais["analise"] = analises
    totais["ref_em_ambiguos"] = ref_em_ambiguos
    return totais


def compare_folders(
    referencia,
    analise,
    modo: str = "nome",
    ignorar_maiusculas: bool = True,
    ignorar_extensao: bool = False,
    progresso=None,
    cancelar=None,
    hasher=None,
) -> dict:
    if modo not in {"nome", "relativo"}:
        raise ValueError("Escolha comparar pelo nome do ficheiro ou pelo caminho relativo.")
    pasta_ref = require_directory(referencia, "referência (C8PA)")
    pasta_ana = require_directory(analise, "análise")
    if pasta_ref == pasta_ana:
        raise ValueError("A pasta de referência e a pasta de análise são a mesma.")
    _check_cancel(cancelar)
    if progresso:
        progresso("referencia", 0, 0, "A ler a pasta de referência…")
    ref_files, avisos_ref = list_images(pasta_ref, progresso, "referencia", cancelar)
    if progresso:
        progresso("analise", 0, 0, "A ler a pasta de análise…")
    ana_files, avisos_ana = list_images(pasta_ana, progresso, "analise", cancelar)
    itens = pair_items(
        ref_files,
        ana_files,
        modo,
        bool(ignorar_maiusculas),
        bool(ignorar_extensao),
        hasher or file_hash,
        cancelar,
        progresso,
    )
    avisos = avisos_ref + avisos_ana
    extensoes = extensions_label()
    if not ref_files and not ana_files:
        avisos.append(f"Não encontrei imagens nestas pastas. Extensões reconhecidas: {extensoes}.")
    elif not ref_files:
        avisos.append("A pasta de referência não tem imagens reconhecidas.")
    elif not ana_files:
        avisos.append(
            "A pasta de análise não tem imagens reconhecidas. "
            "Tudo o que está na referência aparece como em falta."
        )
    return {
        "referencia": str(pasta_ref),
        "analise": str(pasta_ana),
        "opcoes": {
            "modo": modo,
            "ignorar_maiusculas": bool(ignorar_maiusculas),
            "ignorar_extensao": bool(ignorar_extensao),
        },
        "totais": count_totals(itens, len(ref_files), len(ana_files)),
        "avisos": avisos,
        "itens": itens,
    }


def is_filesystem_root(path: Path) -> bool:
    resolvido = path.resolve()
    return resolvido.parent == resolvido


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return path.resolve() != parent.resolve()


def prepare_destination(valor, referencia, analise) -> Path:
    texto = strip_path_text(valor)
    if not texto:
        raise ValueError("Indique a pasta de destino para guardar as cópias.")
    destino = Path(texto).expanduser().resolve()
    if is_filesystem_root(destino):
        raise ValueError("Escolha uma pasta de destino mais específica do que a raiz do disco.")
    if destino.exists() and not destino.is_dir():
        raise ValueError("A pasta de destino existe, mas não é uma pasta.")
    ref = Path(referencia).resolve()
    ana = Path(analise).resolve()
    if destino == ref or is_inside(destino, ref):
        raise ValueError(
            "A pasta de destino não pode ser a pasta de referência nem ficar dentro dela."
        )
    if destino == ana or is_inside(destino, ana):
        raise ValueError(
            "A pasta de destino não pode ser a pasta de análise nem ficar dentro dela."
        )
    return destino


def sanitize_name(nome: str) -> str:
    limpo = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(" .")
    return limpo or "pasta"


def side_names(referencia: str, analise: str) -> tuple[str, str]:
    nome_ref = sanitize_name(Path(referencia).name)
    nome_ana = sanitize_name(Path(analise).name)
    if nome_ref.casefold() == nome_ana.casefold():
        nome_ref = f"{nome_ref}_referencia"
        nome_ana = f"{nome_ana}_analise"
    return nome_ref, nome_ana


def reserve_destination(pasta: Path, rel: str, usados: set) -> Path:
    partes = PurePosixPath(rel).parts
    if not partes or any(parte in {"..", "."} or ":" in parte or "\\" in parte or "/" in parte for parte in partes):
        raise ValueError(f"Caminho relativo inválido: {rel}")
    candidato = pasta.joinpath(*partes)
    stem = candidato.stem
    suffix = candidato.suffix
    parent = candidato.parent
    numero = 2
    while os.path.normcase(str(candidato)) in usados:
        candidato = parent / f"{stem}_{numero}{suffix}"
        numero += 1
    usados.add(os.path.normcase(str(candidato)))
    return candidato


def folders_for(item: dict, destino: Path, nome_ref: str, nome_ana: str):
    estado = item["estado"]
    if estado == "em_falta":
        return destino / "em_falta", None
    if estado == "so_analise":
        return None, destino / "so_na_analise"
    if estado == "diferente":
        base = destino / "conteudo_diferente"
        return base / nome_ref, base / nome_ana
    if estado == "ambiguo":
        base = destino / "ambiguos"
        return base / nome_ref, base / nome_ana
    if estado == "erro":
        base = destino / "erros_de_leitura"
        return base / nome_ref, base / nome_ana
    return None, None


def normalize_include(valor) -> dict:
    incluir = dict(DEFAULT_INCLUDE)
    if isinstance(valor, dict):
        for chave, activo in valor.items():
            if chave in incluir:
                incluir[chave] = bool(activo)
    return incluir


def should_copy(item: dict, incluir: dict, excluir: set) -> bool:
    if item["estado"] == "igual":
        return False
    if item["id"] in excluir:
        return False
    return bool(incluir.get(item["estado"], False))


def ensure_inside(path: Path, root: Path) -> None:
    path.resolve().relative_to(root.resolve())


def copy_one(origem: str, pasta: Path, rel: str, usados: set, destino_raiz: Path) -> str:
    if not Path(origem).is_file():
        raise OSError("O ficheiro já não existe.")
    destino_final = reserve_destination(pasta, rel, usados)
    ensure_inside(destino_final, destino_raiz)
    if Path(origem).resolve() == destino_final.resolve():
        raise OSError("A origem e o destino são o mesmo ficheiro.")
    destino_final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, destino_final)
    return str(destino_final)


def join_field(ficheiros: list, campo: str) -> str:
    return " | ".join(str(ficheiro.get(campo, "")) for ficheiro in ficheiros)


def format_size(tamanho: int) -> str:
    tamanho = int(tamanho)
    if tamanho < 1024:
        return f"{tamanho} B"
    if tamanho < 1024 * 1024:
        return f"{tamanho / 1024:.1f} KB"
    return f"{tamanho / 1024 / 1024:.1f} MB"


def options_sentence(opcoes: dict) -> str:
    modo = "caminho relativo" if opcoes.get("modo") == "relativo" else "nome do ficheiro"
    maiusculas = (
        "sem distinguir maiúsculas de minúsculas"
        if opcoes.get("ignorar_maiusculas")
        else "a distinguir maiúsculas de minúsculas"
    )
    extensao = "ignorando a extensão" if opcoes.get("ignorar_extensao") else "incluindo a extensão"
    return f"Comparação pelo {modo}, {maiusculas}, {extensao}."


def csv_text(resultado: dict, copias: Optional[dict] = None) -> str:
    copias = copias or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow([
        "estado",
        "nome",
        "nota",
        "caminhos_referencia",
        "tamanhos_referencia",
        "hashes_referencia",
        "caminhos_analise",
        "tamanhos_analise",
        "hashes_analise",
        "copias",
    ])
    for item in resultado["itens"]:
        writer.writerow([
            ROTULOS_ESTADO.get(item["estado"], item["estado"]),
            item["nome"],
            item["nota"],
            join_field(item["referencias"], "abs"),
            join_field(item["referencias"], "size"),
            join_field(item["referencias"], "hash"),
            join_field(item["analises"], "abs"),
            join_field(item["analises"], "size"),
            join_field(item["analises"], "hash"),
            " | ".join(copias.get(item["id"], [])),
        ])
    return "\ufeff" + buffer.getvalue()


def summary_lines(resultado: dict, destino: Path, copiados: int, falhas: list) -> list:
    totais = resultado["totais"]
    linhas = [
        "Levantamento de imagens",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Referência (C8PA): {resultado['referencia']}",
        f"Análise: {resultado['analise']}",
        options_sentence(resultado["opcoes"]),
        "",
        "Totais",
        f"- Imagens na referência: {totais['referencia']}",
        f"- Imagens na análise: {totais['analise']}",
        f"- Em falta: {totais['em_falta']}",
        f"- Conteúdo diferente: {totais['diferente']}",
        f"- Iguais: {totais['igual']}",
        f"- Só na análise: {totais['so_analise']}",
        f"- Ambíguos: {totais['ambiguo']}",
        f"- Erros de leitura: {totais['erro']}",
        "",
        f"Ficheiros copiados: {copiados}",
        f"Pasta de destino: {destino}",
        "O CSV usa ponto e vírgula para abrir no Excel e está em UTF-8.",
        "A referência e a análise não foram alteradas.",
        "",
    ]
    for estado in ESTADOS:
        grupo = [item for item in resultado["itens"] if item["estado"] == estado]
        if not grupo:
            continue
        linhas.append(f"== {ROTULOS_ESTADO[estado]} ==")
        for item in grupo:
            refs = join_field(item["referencias"], "rel") or "—"
            anas = join_field(item["analises"], "rel") or "—"
            linhas.append(f"- {item['nome']} | referência: {refs} | análise: {anas}")
        linhas.append("")
    if falhas:
        linhas.append("== falhas ao copiar ==")
        for falha in falhas:
            linhas.append(f"- {falha['origem']}: {falha['motivo']}")
        linhas.append("")
    return linhas


def write_reports(destino: Path, resultado: dict, copiados: int, falhas: list, copias: dict) -> tuple[Path, Path]:
    csv_path = destino / "relatorio.csv"
    txt_path = destino / "resumo.txt"
    csv_path.write_bytes(csv_text(resultado, copias).encode("utf-8"))
    texto = "\r\n".join(summary_lines(resultado, destino, copiados, falhas)) + "\r\n"
    txt_path.write_text(texto, encoding="utf-8")
    return csv_path, txt_path


def copy_differences(resultado: dict, destino, incluir=None, excluir=None, progresso=None, cancelar=None) -> dict:
    destino = prepare_destination(destino, resultado["referencia"], resultado["analise"])
    destino.mkdir(parents=True, exist_ok=True)
    incluir = normalize_include(incluir)
    excluir = set(excluir or [])
    nome_ref, nome_ana = side_names(resultado["referencia"], resultado["analise"])
    seleccionados = [item for item in resultado["itens"] if should_copy(item, incluir, excluir)]
    planos = []
    for item in seleccionados:
        pasta_ref, pasta_ana = folders_for(item, destino, nome_ref, nome_ana)
        if pasta_ref:
            for ficheiro in item["referencias"]:
                planos.append((item, ficheiro, pasta_ref))
        if pasta_ana:
            for ficheiro in item["analises"]:
                planos.append((item, ficheiro, pasta_ana))

    usados = set()
    falhas = []
    copias = defaultdict(list)
    total = len(planos)
    for indice, (item, ficheiro, pasta) in enumerate(planos, start=1):
        _check_cancel(cancelar)
        if progresso:
            progresso("copiar", indice, total, f"A copiar… {indice} de {total}")
        try:
            copiado = copy_one(ficheiro["abs"], pasta, ficheiro["rel"], usados, destino)
        except (OSError, ValueError) as exc:
            motivo = getattr(exc, "strerror", None) or str(exc)
            falhas.append({"origem": ficheiro["abs"], "motivo": motivo})
            continue
        copias[item["id"]].append(copiado)

    try:
        csv_path, txt_path = write_reports(destino, resultado, sum(len(v) for v in copias.values()), falhas, copias)
        relatorio = str(csv_path)
        resumo_txt = str(txt_path)
    except OSError as exc:
        falhas.append({
            "origem": str(destino),
            "motivo": f"Não consegui escrever o relatório ({exc.strerror or exc}).",
        })
        relatorio = ""
        resumo_txt = ""

    return {
        "copiados": sum(len(v) for v in copias.values()),
        "falhas": falhas,
        "destino": str(destino),
        "relatorio": relatorio,
        "resumo_txt": resumo_txt,
    }


def item_matches(item: dict, consulta: str) -> bool:
    partes = [item.get("nome", ""), item.get("nota", ""), item.get("chave", "")]
    for lado in ("referencias", "analises"):
        for ficheiro in item[lado]:
            partes.append(ficheiro.get("rel", ""))
            partes.append(ficheiro.get("abs", ""))
            partes.append(ficheiro.get("nome", ""))
    return any(consulta in (parte or "").casefold() for parte in partes)


def filter_items(resultado: dict, estado: str, consulta: str, offset: int, limit: int) -> dict:
    if estado not in ESTADOS:
        raise ValueError("Categoria desconhecida.")
    if limit < 1 or limit > 200:
        raise ValueError("Limite inválido.")
    if offset < 0:
        raise ValueError("Página inválida.")
    consulta = (consulta or "").casefold().strip()
    filtrados = []
    for item in resultado["itens"]:
        if item["estado"] != estado:
            continue
        if consulta and not item_matches(item, consulta):
            continue
        filtrados.append(item)
    return {"total": len(filtrados), "itens": filtrados[offset:offset + limit]}


def summary_public(resultado: dict) -> dict:
    return {
        "referencia": resultado["referencia"],
        "analise": resultado["analise"],
        "opcoes": resultado["opcoes"],
        "totais": resultado["totais"],
        "avisos": resultado["avisos"],
    }


def load_recent() -> dict:
    try:
        dados = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(dados, dict):
        return {}
    return dados


def save_recent(dados: dict) -> None:
    payload = {
        "referencia": strip_path_text(dados.get("referencia", "")),
        "analise": strip_path_text(dados.get("analise", "")),
        "destino": strip_path_text(dados.get("destino", "")),
        "modo": dados.get("modo") if dados.get("modo") in {"nome", "relativo"} else "nome",
        "ignorar_maiusculas": bool(dados.get("ignorar_maiusculas", True)),
        "ignorar_extensao": bool(dados.get("ignorar_extensao", False)),
    }
    try:
        CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def interpret_picker(codigo: int, saida: str, erro: str) -> dict:
    if codigo == 2 or "tkinter_indisponivel" in (erro or ""):
        return {
            "erro": (
                "Neste computador o seletor de pastas não está disponível. Cole o caminho. "
                "No Explorador de Ficheiros, clique na barra de endereço, copie e cole aqui."
            )
        }
    if codigo != 0:
        return {"erro": "Não consegui abrir a janela de escolha. Cole o caminho da pasta."}
    caminho = (saida or "").strip().strip("\r")
    if not caminho:
        return {"cancelado": True}
    return {"caminho": caminho}


def choose_folder() -> dict:
    codigo = (
        "import sys\n"
        "try:\n"
        "    import tkinter as tk\n"
        "    from tkinter import filedialog\n"
        "except Exception:\n"
        "    sys.stderr.write('tkinter_indisponivel')\n"
        "    raise SystemExit(2)\n"
        "root = tk.Tk()\n"
        "root.withdraw()\n"
        "try:\n"
        "    root.attributes('-topmost', True)\n"
        "except Exception:\n"
        "    pass\n"
        "caminho = filedialog.askdirectory(title='Escolher pasta') or ''\n"
        "sys.stdout.write(caminho)\n"
        "root.destroy()\n"
    )
    kwargs = {"capture_output": True, "text": True, "timeout": 300}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = startupinfo
    try:
        proc = subprocess.run([sys.executable, "-c", codigo], **kwargs)
    except subprocess.TimeoutExpired:
        return {"erro": "A janela de escolha da pasta demorou demasiado. Cole o caminho."}
    except OSError:
        return {"erro": "Não consegui abrir a janela de escolha. Cole o caminho da pasta."}
    return interpret_picker(proc.returncode, proc.stdout, proc.stderr)


def open_folder(caminho) -> dict:
    pasta = require_directory(caminho, "destino")
    try:
        if sys.platform == "win32":
            os.startfile(pasta)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(pasta)], check=False)
        else:
            subprocess.run(["xdg-open", str(pasta)], check=False)
    except OSError as exc:
        raise ValueError(f"Não consegui abrir a pasta ({exc.strerror or exc}).") from exc
    return {"ok": True}


def render_page() -> str:
    html = PAGE_PATH.read_text(encoding="utf-8")
    return html.replace("<!--EXTENSOES-->", extensions_label())


class GestorTrabalhos:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs = {}

    def criar(self) -> str:
        job = {
            "id": uuid.uuid4().hex,
            "estado": "a_correr",
            "fase": "inicio",
            "mensagem": "A preparar a comparação…",
            "atual": 0,
            "total": 0,
            "erro": "",
            "resultado": None,
            "copia": None,
            "cancelar": False,
            "criado": time.time(),
        }
        with self._lock:
            self._limpar()
            self._jobs[job["id"]] = job
        return job["id"]

    def obter(self, job_id: str):
        with self._lock:
            return self._jobs.get(job_id)

    def actualizar(self, job_id: str, **campos) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.update(campos)

    def actualizar_copia(self, job_id: str, **campos) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if job.get("copia") is None:
                job["copia"] = {}
            job["copia"].update(campos)

    def cancelar(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            job["cancelar"] = True
            return True

    def instantaneo(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            copia = job.get("copia")
            copia_publica = None
            if copia:
                copia_publica = {
                    "estado": copia.get("estado"),
                    "mensagem": copia.get("mensagem", ""),
                    "atual": copia.get("atual", 0),
                    "total": copia.get("total", 0),
                    "erro": copia.get("erro", ""),
                    "resultado": copia.get("resultado"),
                }
            return {
                "id": job["id"],
                "estado": job["estado"],
                "fase": job["fase"],
                "mensagem": job["mensagem"],
                "atual": job["atual"],
                "total": job["total"],
                "erro": job["erro"],
                "resumo": summary_public(job["resultado"]) if job.get("resultado") else None,
                "copia": copia_publica,
            }

    def _limpar(self) -> None:
        if len(self._jobs) <= 12:
            return
        terminados = []
        for job in self._jobs.values():
            copia = job.get("copia") or {}
            if job["estado"] == "a_correr" or copia.get("estado") == "a_correr":
                continue
            terminados.append(job)
        terminados.sort(key=lambda job: job["criado"])
        for job in terminados[: max(0, len(self._jobs) - 8)]:
            self._jobs.pop(job["id"], None)


GESTOR = GestorTrabalhos()


def _cancelar_job(job_id: str) -> bool:
    job = GESTOR.obter(job_id)
    return bool(job and job.get("cancelar"))


def worker_comparar(job_id: str, referencia: str, analise: str, modo: str, ignorar_maiusculas: bool, ignorar_extensao: bool) -> None:
    def progresso(fase, atual, total, mensagem):
        GESTOR.actualizar(job_id, fase=fase, atual=atual, total=total, mensagem=mensagem)

    try:
        resultado = compare_folders(
            referencia,
            analise,
            modo=modo,
            ignorar_maiusculas=ignorar_maiusculas,
            ignorar_extensao=ignorar_extensao,
            progresso=progresso,
            cancelar=lambda: _cancelar_job(job_id),
        )
        GESTOR.actualizar(
            job_id,
            estado="concluido",
            resultado=resultado,
            mensagem="Comparação concluída.",
            fase="concluido",
            atual=1,
            total=1,
        )
    except Cancelado:
        GESTOR.actualizar(job_id, estado="cancelado", mensagem="Comparação cancelada.", erro="")
    except ValueError as exc:
        GESTOR.actualizar(job_id, estado="erro", erro=str(exc), mensagem=str(exc))
    except Exception:
        traceback.print_exc()
        GESTOR.actualizar(
            job_id,
            estado="erro",
            erro="Ocorreu um erro ao comparar as pastas.",
            mensagem="Ocorreu um erro ao comparar as pastas.",
        )


def worker_copiar(job_id: str, destino: str, incluir: dict, excluir: list) -> None:
    job = GESTOR.obter(job_id)
    if not job or not job.get("resultado"):
        GESTOR.actualizar_copia(job_id, estado="erro", erro="Já não tenho o resultado da comparação.")
        return

    def progresso(fase, atual, total, mensagem):
        GESTOR.actualizar_copia(job_id, fase=fase, atual=atual, total=total, mensagem=mensagem)

    try:
        resultado = copy_differences(
            job["resultado"],
            destino,
            incluir=incluir,
            excluir=excluir,
            progresso=progresso,
            cancelar=lambda: _cancelar_job(job_id),
        )
        GESTOR.actualizar_copia(
            job_id,
            estado="concluido",
            mensagem="Cópia concluída.",
            resultado=resultado,
            atual=resultado["copiados"],
            total=resultado["copiados"],
        )
    except Cancelado:
        GESTOR.actualizar_copia(
            job_id,
            estado="cancelado",
            mensagem="Cópia cancelada. Os ficheiros já copiados mantêm-se na pasta de destino.",
            erro="",
        )
    except ValueError as exc:
        GESTOR.actualizar_copia(job_id, estado="erro", erro=str(exc), mensagem=str(exc))
    except Exception:
        traceback.print_exc()
        GESTOR.actualizar_copia(
            job_id,
            estado="erro",
            erro="Ocorreu um erro ao copiar as imagens.",
            mensagem="Ocorreu um erro ao copiar as imagens.",
        )


def find_image(resultado: dict, item_id: str, lado: str, indice: int) -> str:
    chave_lado = {"referencia": "referencias", "analise": "analises"}.get(lado)
    if not chave_lado:
        raise ValueError("Imagem inválida.")
    for item in resultado["itens"]:
        if item["id"] != item_id:
            continue
        ficheiros = item[chave_lado]
        if indice >= len(ficheiros):
            raise NaoEncontrado()
        return ficheiros[indice]["abs"]
    raise NaoEncontrado()


class AppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        pedido = args[0] if args else ""
        if isinstance(pedido, str) and "/api/estado" in pedido:
            return
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self._bytes(200, render_page().encode("utf-8"), "text/html; charset=utf-8")
            elif parsed.path == "/api/estado":
                self._estado(qs)
            elif parsed.path == "/api/itens":
                self._itens(qs)
            elif parsed.path == "/api/imagem":
                self._imagem(qs)
            elif parsed.path == "/api/relatorio":
                self._relatorio(qs)
            elif parsed.path == "/api/ultimas":
                self._json(200, load_recent())
            elif parsed.path == "/favicon.ico":
                self._bytes(204, b"", "image/x-icon")
            else:
                self._erro(404, "Não encontrado.")
        except ValueError as exc:
            self._erro(400, str(exc))
        except NaoEncontrado:
            self._erro(404, "Já não tenho este resultado. Volte a comparar.")
        except Exception:
            traceback.print_exc()
            self._erro(500, "Ocorreu um erro interno.")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            dados = self._ler_json()
            if parsed.path == "/api/comparar":
                self._comparar(dados)
            elif parsed.path == "/api/copiar":
                self._copiar(dados)
            elif parsed.path == "/api/escolher":
                self._json(200, choose_folder())
            elif parsed.path == "/api/exemplo":
                try:
                    criado = create_example(EXAMPLE_DIR)
                except OSError as exc:
                    raise ValueError(
                        f"Não consegui criar as pastas de exemplo ({exc.strerror or exc})."
                    ) from exc
                self._json(200, criado)
            elif parsed.path == "/api/cancelar":
                self._cancelar(dados)
            elif parsed.path == "/api/abrir":
                self._json(200, open_folder(dados.get("caminho")))
            else:
                self._erro(404, "Não encontrado.")
        except ValueError as exc:
            self._erro(400, str(exc))
        except NaoEncontrado:
            self._erro(404, "Já não tenho este resultado. Volte a comparar.")
        except Exception:
            traceback.print_exc()
            self._erro(500, "Ocorreu um erro interno.")

    def _ler_json(self) -> dict:
        try:
            tamanho = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError as exc:
            raise ValueError("Pedido inválido.") from exc
        if tamanho < 0 or tamanho > 5_000_000:
            raise ValueError("Pedido inválido.")
        bruto = self.rfile.read(tamanho) if tamanho else b"{}"
        try:
            dados = json.loads(bruto.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("O pedido não está em JSON válido.") from exc
        if not isinstance(dados, dict):
            raise ValueError("O pedido não está em JSON válido.")
        return dados

    def _comparar(self, dados: dict) -> None:
        modo = dados.get("modo") or "nome"
        ignorar_maiusculas = bool(dados.get("ignorar_maiusculas", True))
        ignorar_extensao = bool(dados.get("ignorar_extensao", False))
        referencia = require_directory(dados.get("referencia"), "referência (C8PA)")
        analise = require_directory(dados.get("analise"), "análise")
        if referencia == analise:
            raise ValueError("A pasta de referência e a pasta de análise são a mesma.")
        if modo not in {"nome", "relativo"}:
            raise ValueError("Escolha comparar pelo nome do ficheiro ou pelo caminho relativo.")
        save_recent({
            "referencia": str(referencia),
            "analise": str(analise),
            "destino": dados.get("destino", ""),
            "modo": modo,
            "ignorar_maiusculas": ignorar_maiusculas,
            "ignorar_extensao": ignorar_extensao,
        })
        job_id = GESTOR.criar()
        threading.Thread(
            target=worker_comparar,
            args=(job_id, str(referencia), str(analise), modo, ignorar_maiusculas, ignorar_extensao),
            daemon=True,
        ).start()
        self._json(200, {"id": job_id})

    def _copiar(self, dados: dict) -> None:
        job_id = str(dados.get("id") or "")
        job = GESTOR.obter(job_id)
        if not job or not job.get("resultado"):
            raise NaoEncontrado()
        if job["estado"] == "a_correr":
            raise ValueError("Espere que a comparação termine.")
        copia = job.get("copia") or {}
        if copia.get("estado") == "a_correr":
            raise ValueError("Ainda estou a copiar.")
        excluir = dados.get("excluir") or []
        if not isinstance(excluir, list) or not all(isinstance(item, str) for item in excluir):
            raise ValueError("A seleção de imagens a excluir não é válida.")
        destino = prepare_destination(dados.get("destino"), job["resultado"]["referencia"], job["resultado"]["analise"])
        incluir = normalize_include(dados.get("incluir"))
        save_recent({
            "referencia": job["resultado"]["referencia"],
            "analise": job["resultado"]["analise"],
            "destino": str(destino),
            "modo": job["resultado"]["opcoes"]["modo"],
            "ignorar_maiusculas": job["resultado"]["opcoes"]["ignorar_maiusculas"],
            "ignorar_extensao": job["resultado"]["opcoes"]["ignorar_extensao"],
        })
        GESTOR.actualizar(job_id, cancelar=False)
        GESTOR.actualizar_copia(
            job_id,
            estado="a_correr",
            mensagem="A copiar…",
            atual=0,
            total=0,
            erro="",
            resultado=None,
        )
        threading.Thread(
            target=worker_copiar,
            args=(job_id, str(destino), incluir, excluir),
            daemon=True,
        ).start()
        self._json(200, {"id": job_id})

    def _cancelar(self, dados: dict) -> None:
        job_id = str(dados.get("id") or "")
        if not GESTOR.cancelar(job_id):
            raise NaoEncontrado()
        self._json(200, {"ok": True})

    def _estado(self, qs: dict) -> None:
        instantaneo = GESTOR.instantaneo(primeiro(qs, "id"))
        if not instantaneo:
            raise NaoEncontrado()
        self._json(200, instantaneo)

    def _itens(self, qs: dict) -> None:
        job = GESTOR.obter(primeiro(qs, "id"))
        if not job or not job.get("resultado"):
            raise NaoEncontrado()
        offset = inteiro(qs, "offset", 0)
        limit = inteiro(qs, "limit", 24)
        self._json(200, filter_items(
            job["resultado"],
            primeiro(qs, "estado"),
            primeiro(qs, "q", obrigatorio=False),
            offset,
            limit,
        ))

    def _imagem(self, qs: dict) -> None:
        job = GESTOR.obter(primeiro(qs, "id"))
        if not job or not job.get("resultado"):
            raise NaoEncontrado()
        caminho = find_image(
            job["resultado"],
            primeiro(qs, "item"),
            primeiro(qs, "lado"),
            inteiro(qs, "indice", 0),
        )
        self._ficheiro(caminho)

    def _relatorio(self, qs: dict) -> None:
        job = GESTOR.obter(primeiro(qs, "id"))
        if not job or not job.get("resultado"):
            raise NaoEncontrado()
        corpo = csv_text(job["resultado"]).encode("utf-8")
        self._bytes(
            200,
            corpo,
            "text/csv; charset=utf-8",
            download_name="relatorio.csv",
        )

    def _json(self, codigo: int, payload: dict) -> None:
        self._bytes(
            codigo,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _erro(self, codigo: int, mensagem: str) -> None:
        self._json(codigo, {"erro": mensagem})

    def _bytes(self, codigo: int, body: bytes, content_type: str, download_name: str = "") -> None:
        try:
            self.send_response(codigo)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
            )
            if download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.end_headers()
            if codigo != 204 and body:
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _ficheiro(self, caminho: str) -> None:
        path = Path(caminho)
        try:
            tamanho = path.stat().st_size
            handle = path.open("rb")
        except OSError as exc:
            raise NaoEncontrado() from exc
        tipo = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(tamanho))
            self.send_header("Cache-Control", "private, max-age=300")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            while True:
                bloco = handle.read(256 * 1024)
                if not bloco:
                    break
                self.wfile.write(bloco)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            handle.close()


def primeiro(qs: dict, chave: str, obrigatorio: bool = True) -> str:
    valores = qs.get(chave) or []
    if not valores or valores[0] == "":
        if obrigatorio:
            raise ValueError("Falta um dado do pedido.")
        return ""
    return valores[0]


def inteiro(qs: dict, chave: str, omissao: int) -> int:
    bruto = primeiro(qs, chave, obrigatorio=False)
    if bruto == "":
        return omissao
    try:
        return int(bruto)
    except ValueError as exc:
        raise ValueError("Número inválido.") from exc


def criar_servidor(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    servidor = ThreadingHTTPServer((host, port), AppHandler)
    servidor.daemon_threads = True
    return servidor


def main(argv=None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description="Levantamento de imagens entre a pasta C8PA e uma pasta de análise."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not PAGE_PATH.is_file():
        print(f"Não encontrei {PAGE_PATH.name} ao lado deste programa.", file=sys.stderr)
        return 1
    servidor = None
    porta = None
    for candidato in range(args.port, args.port + 10):
        try:
            servidor = criar_servidor(args.host, candidato)
            porta = candidato
            break
        except OSError:
            continue
    if servidor is None or porta is None:
        print("Não consegui abrir uma porta local para o programa.", file=sys.stderr)
        return 1
    url = f"http://{args.host}:{porta}/"
    print(url, flush=True)
    print("Deixe esta janela aberta enquanto compara as pastas. Para sair, prima Ctrl+C.", flush=True)
    if not args.no_browser:
        threading.Thread(target=lambda: abrir_browser(url), daemon=True).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nPrograma encerrado.")
    finally:
        servidor.server_close()
    return 0


def abrir_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        print(f"Abra este endereço no browser: {url}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
