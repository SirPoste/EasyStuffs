import hashlib
import json
import re
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import comparar_imagens as app


def rels(resultado, estado, lado="referencias"):
    saida = []
    for item in resultado["itens"]:
        if item["estado"] != estado:
            continue
        for ficheiro in item[lado]:
            saida.append(ficheiro["rel"])
    return sorted(saida)


def nomes(resultado, estado):
    return sorted(item["nome"] for item in resultado["itens"] if item["estado"] == estado)


class LogicaTest(unittest.TestCase):
    def test_png_e_hash(self):
        a = app.solid_png(4, 4, (1, 2, 3))
        b = app.solid_png(4, 4, (1, 2, 4))
        self.assertTrue(a.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IEND", a)
        self.assertNotEqual(a, b)
        self.assertEqual(a, app.solid_png(4, 4, (1, 2, 3)))
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "f.bin"
            caminho.write_bytes(b"abc")
            self.assertEqual(app.file_hash(str(caminho)), hashlib.sha256(b"abc").hexdigest())

    def test_exemplo_pelo_nome(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            resultado = app.compare_folders(pastas["referencia"], pastas["analise"])
            totais = resultado["totais"]
            self.assertEqual(totais["referencia"], 8)
            self.assertEqual(totais["analise"], 6)
            self.assertEqual(totais["em_falta"], 2)
            self.assertEqual(totais["diferente"], 1)
            self.assertEqual(totais["igual"], 3)
            self.assertEqual(totais["so_analise"], 1)
            self.assertEqual(totais["ambiguo"], 1)
            self.assertEqual(totais["ref_em_ambiguos"], 2)
            self.assertEqual(nomes(resultado, "em_falta"), ["anilha.png", "cavilha_ção.png"])
            self.assertEqual(nomes(resultado, "diferente"), ["porca.png"])
            self.assertFalse(any(item["nome"] == "notas.txt" for item in resultado["itens"]))
            porca = next(item for item in resultado["itens"] if item["nome"] == "porca.png")
            self.assertNotEqual(
                (porca["referencias"][0]["size"], porca["referencias"][0]["hash"]),
                (porca["analises"][0]["size"], porca["analises"][0]["hash"]),
            )

    def test_exemplo_pelo_caminho(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            resultado = app.compare_folders(pastas["referencia"], pastas["analise"], modo="relativo")
            self.assertEqual(rels(resultado, "igual"), ["mesmo/anel.png", "pecas/parafuso.png"])
            self.assertEqual(rels(resultado, "em_falta"), [
                "dup/a/peca.png",
                "dup/b/peca.png",
                "pecas/anilha.png",
                "pecas/cavilha_ção.png",
                "pecas/porca.png",
                "tampa.JPG",
            ])
            self.assertEqual(rels(resultado, "so_analise", "analises"), [
                "extra/etiqueta.png",
                "linha/porca.png",
                "peca.png",
                "sub/tampa.jpg",
            ])
            self.assertEqual(resultado["totais"]["diferente"], 0)
            self.assertEqual(resultado["totais"]["ambiguo"], 0)

    def test_maiusculas_e_extensao(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ref = raiz / "ref"
            ana = raiz / "ana"
            conteudo = b"igual-mesmo"
            (ref).mkdir()
            ana.mkdir()
            (ref / "Foto.png").write_bytes(conteudo)
            (ana / "foto.png").write_bytes(conteudo)
            sensivel = app.compare_folders(ref, ana, ignorar_maiusculas=False)
            self.assertEqual(sensivel["totais"]["igual"], 0)
            self.assertEqual(sensivel["totais"]["em_falta"], 1)
            self.assertEqual(sensivel["totais"]["so_analise"], 1)
            insensivel = app.compare_folders(ref, ana, ignorar_maiusculas=True)
            self.assertEqual(insensivel["totais"]["igual"], 1)

            (ref / "extra.jpg").write_bytes(b"bytes-iguais")
            (ana / "extra.png").write_bytes(b"bytes-iguais")
            com_ext = app.compare_folders(ref, ana, ignorar_extensao=False)
            self.assertEqual(com_ext["totais"]["igual"], 1)
            sem_ext = app.compare_folders(ref, ana, ignorar_extensao=True)
            self.assertEqual(sem_ext["totais"]["igual"], 2)

    def test_mesmo_tamanho_conteudo_diferente(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ref = raiz / "C8PA"
            ana = raiz / "analise"
            ref.mkdir()
            ana.mkdir()
            (ref / "a.png").write_bytes(b"\x89PNG" + b"A" * 20)
            (ana / "a.png").write_bytes(b"\x89PNG" + b"B" * 20)
            (ref / "b.png").write_bytes(b"aa")
            (ana / "b.png").write_bytes(b"bbb")
            resultado = app.compare_folders(ref, ana)
            por_nome = {item["nome"]: item for item in resultado["itens"]}
            self.assertEqual(por_nome["a.png"]["estado"], "diferente")
            self.assertNotEqual(por_nome["a.png"]["referencias"][0]["hash"], por_nome["a.png"]["analises"][0]["hash"])
            self.assertEqual(por_nome["b.png"]["estado"], "diferente")
            self.assertEqual(por_nome["b.png"]["referencias"][0]["hash"], "")

    def test_copia_nao_altera_origem(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp) / "exemplo")
            ref = Path(pastas["referencia"])
            ana = Path(pastas["analise"])
            antes = {caminho: caminho.read_bytes() for caminho in ref.rglob("*") if caminho.is_file()}
            antes.update({caminho: caminho.read_bytes() for caminho in ana.rglob("*") if caminho.is_file()})
            resultado = app.compare_folders(ref, ana)
            destino = Path(tmp) / "copias"
            copia = app.copy_differences(resultado, destino)
            self.assertEqual(copia["falhas"], [])
            self.assertEqual(copia["copiados"], 7)
            self.assertTrue((destino / "em_falta" / "pecas" / "anilha.png").is_file())
            self.assertTrue((destino / "em_falta" / "pecas" / "cavilha_ção.png").is_file())
            self.assertTrue((destino / "conteudo_diferente" / "C8PA" / "pecas" / "porca.png").is_file())
            self.assertTrue((destino / "conteudo_diferente" / "analise" / "linha" / "porca.png").is_file())
            self.assertTrue((destino / "ambiguos" / "C8PA" / "dup" / "a" / "peca.png").is_file())
            self.assertTrue((destino / "ambiguos" / "C8PA" / "dup" / "b" / "peca.png").is_file())
            self.assertTrue((destino / "ambiguos" / "analise" / "peca.png").is_file())
            self.assertFalse((destino / "so_na_analise").exists())
            self.assertFalse(list(destino.rglob("parafuso.png")))
            self.assertFalse(list(destino.rglob("anel.png")))
            self.assertEqual(
                (destino / "em_falta" / "pecas" / "anilha.png").read_bytes(),
                (ref / "pecas" / "anilha.png").read_bytes(),
            )
            self.assertNotEqual(
                (destino / "conteudo_diferente" / "C8PA" / "pecas" / "porca.png").read_bytes(),
                (destino / "conteudo_diferente" / "analise" / "linha" / "porca.png").read_bytes(),
            )
            depois = {caminho: caminho.read_bytes() for caminho in ref.rglob("*") if caminho.is_file()}
            depois.update({caminho: caminho.read_bytes() for caminho in ana.rglob("*") if caminho.is_file()})
            self.assertEqual(antes, depois)
            csv = (destino / "relatorio.csv").read_text(encoding="utf-8-sig")
            self.assertIn("cavilha_ção.png", csv)
            self.assertIn("em falta", csv)
            self.assertIn(";", csv)
            self.assertTrue((destino / "resumo.txt").is_file())

    def test_copia_respeita_exclusao_e_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            resultado = app.compare_folders(pastas["referencia"], pastas["analise"])
            anilha = next(item for item in resultado["itens"] if item["nome"] == "anilha.png")
            destino = Path(tmp) / "so_algumas"
            incluir = dict(app.DEFAULT_INCLUDE)
            incluir["so_analise"] = True
            copia = app.copy_differences(resultado, destino, incluir=incluir, excluir={anilha["id"]})
            self.assertEqual(copia["falhas"], [])
            self.assertFalse((destino / "em_falta" / "pecas" / "anilha.png").exists())
            self.assertTrue((destino / "em_falta" / "pecas" / "cavilha_ção.png").is_file())
            self.assertTrue((destino / "so_na_analise" / "extra" / "etiqueta.png").is_file())

    def test_destino_recusado(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            resultado = app.compare_folders(pastas["referencia"], pastas["analise"])
            with self.assertRaises(ValueError):
                app.copy_differences(resultado, Path(pastas["referencia"]) / "saida")
            with self.assertRaises(ValueError):
                app.copy_differences(resultado, Path(pastas["analise"]) / "saida")
            with self.assertRaises(ValueError):
                app.prepare_destination("/", pastas["referencia"], pastas["analise"])
            ficheiro = Path(tmp) / "nao_pasta"
            ficheiro.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                app.copy_differences(resultado, ficheiro)
            with self.assertRaises(ValueError):
                app.compare_folders(pastas["referencia"], pastas["referencia"])

    def test_caminhos_e_seletor(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp) / "C8PA"
            pasta.mkdir()
            self.assertEqual(app.require_directory(f'  "{pasta}"  ', "referência (C8PA)"), pasta.resolve())
        self.assertIn("Cole o caminho", app.interpret_picker(2, "", "tkinter_indisponivel")["erro"])
        self.assertTrue(app.interpret_picker(0, "  \n", "")["cancelado"])
        self.assertEqual(app.interpret_picker(0, "D:\\C8PA\r\n", "")["caminho"], "D:\\C8PA")
        usados = set()
        base = Path("/tmp/reservar-destino-teste")
        primeiro = app.reserve_destination(base, "pecas/a.png", usados)
        segundo = app.reserve_destination(base, "pecas/a.png", usados)
        self.assertEqual(primeiro.name, "a.png")
        self.assertEqual(segundo.name, "a_2.png")
        with self.assertRaises(ValueError):
            app.reserve_destination(Path(tmp) / "out", "../segredo.png", set())

    def test_filtro_e_pagina(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            resultado = app.compare_folders(pastas["referencia"], pastas["analise"])
            pagina = app.filter_items(resultado, "em_falta", "cavilha", 0, 24)
            self.assertEqual(pagina["total"], 1)
            self.assertIn("ção", pagina["itens"][0]["nome"])
            html = app.render_page()
            self.assertIn("Levantamento de imagens", html)
            self.assertIn(".png", html)
            self.assertNotIn("<!--EXTENSOES-->", html)
            formulario = html.split("<script>", 1)[0]
            for bloco in re.findall(r"<label\b[^>]*>.*?</label>", formulario, flags=re.S):
                self.assertNotIn("<button", bloco)

    def test_cancelar(self):
        with tempfile.TemporaryDirectory() as tmp:
            pastas = app.create_example(Path(tmp))
            with self.assertRaises(app.Cancelado):
                app.compare_folders(pastas["referencia"], pastas["analise"], cancelar=lambda: True)


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name)
        app.CONFIG_PATH = cls.base / "ultimas.json"
        app.EXAMPLE_DIR = cls.base / "exemplo"
        cls.server = app.criar_servidor()
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def url(self, caminho):
        return f"http://127.0.0.1:{self.port}{caminho}"

    def post(self, caminho, payload):
        dados = json.dumps(payload).encode("utf-8")
        pedido = urllib.request.Request(
            self.url(caminho),
            data=dados,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return json.loads(resposta.read().decode("utf-8")), resposta.status

    def get(self, caminho):
        with urllib.request.urlopen(self.url(caminho), timeout=10) as resposta:
            corpo = resposta.read()
            tipo = resposta.headers.get("Content-Type", "")
            return corpo, tipo, resposta.status

    def test_fluxo(self):
        pagina, tipo, _ = self.get("/")
        self.assertIn("text/html", tipo)
        self.assertIn("Levantamento de imagens".encode(), pagina)
        exemplo, _ = self.post("/api/exemplo", {})
        self.assertTrue(Path(exemplo["referencia"]).is_dir())
        job, _ = self.post("/api/comparar", {
            "referencia": exemplo["referencia"],
            "analise": exemplo["analise"],
            "destino": exemplo["destino"],
            "modo": "nome",
            "ignorar_maiusculas": True,
            "ignorar_extensao": False,
        })
        estado = {}
        for _ in range(100):
            corpo, _, _ = self.get("/api/estado?id=" + job["id"])
            estado = json.loads(corpo.decode("utf-8"))
            if estado["estado"] != "a_correr":
                break
            time.sleep(0.05)
        self.assertEqual(estado["estado"], "concluido")
        self.assertEqual(estado["resumo"]["totais"]["em_falta"], 2)
        guardado = json.loads(app.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(guardado["referencia"], exemplo["referencia"])
        itens_raw, _, _ = self.get("/api/itens?id=" + job["id"] + "&estado=em_falta&q=&offset=0&limit=24")
        itens = json.loads(itens_raw.decode("utf-8"))
        self.assertEqual(itens["total"], 2)
        imagem, tipo_imagem, _ = self.get(
            "/api/imagem?id=%s&item=%s&lado=referencia&indice=0" % (job["id"], itens["itens"][0]["id"])
        )
        self.assertTrue(imagem.startswith(b"\x89PNG"))
        self.assertIn("image/png", tipo_imagem)
        self.post("/api/copiar", {
            "id": job["id"],
            "destino": exemplo["destino"],
            "incluir": {"em_falta": True, "diferente": True, "ambiguo": False, "so_analise": False, "erro": False},
            "excluir": [],
        })
        copia = {}
        for _ in range(100):
            corpo, _, _ = self.get("/api/estado?id=" + job["id"])
            estado = json.loads(corpo.decode("utf-8"))
            copia = estado.get("copia") or {}
            if copia.get("estado") not in {None, "a_correr"}:
                break
            time.sleep(0.05)
        self.assertEqual(copia["estado"], "concluido")
        self.assertEqual(copia["resultado"]["copiados"], 4)
        destino = Path(exemplo["destino"])
        self.assertTrue((destino / "em_falta" / "pecas" / "cavilha_ção.png").is_file())
        self.assertTrue((destino / "conteudo_diferente" / "C8PA" / "pecas" / "porca.png").is_file())
        self.assertFalse((destino / "ambiguos").exists())
        relatorio, tipo_csv, _ = self.get("/api/relatorio?id=" + job["id"])
        self.assertIn(b"cavilha", relatorio)
        self.assertIn("text/csv", tipo_csv)

    def test_pasta_inexistente(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/comparar", {"referencia": str(self.base / "nao-existe"), "analise": str(self.base)})
        self.assertEqual(ctx.exception.code, 400)
        corpo = json.loads(ctx.exception.read().decode("utf-8"))
        self.assertIn("Não encontrei", corpo["erro"])


if __name__ == "__main__":
    unittest.main()
