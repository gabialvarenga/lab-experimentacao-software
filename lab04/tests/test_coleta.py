"""Testes da coleta, sem rede: a sessão HTTP é substituída por uma API fictícia."""

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from lab04 import coleta

BASE = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


def iso(momento):
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


class Resposta:
    def __init__(self, status=200, corpo=None, cabecalhos=None):
        self.status_code = status
        self._corpo = corpo
        self.headers = cabecalhos or {}

    def json(self):
        return self._corpo


class ApiFalsa:
    """Responde buscas e revisões a partir de PRs fictícios, e registra as chamadas."""

    def __init__(self, prs):
        self.prs = prs   # numero -> dict(mes, autor_tipo, horas_merge, revisao_h, com_comentario)
        self.chamadas = []

    def get(self, url, params=None, headers=None, timeout=None):
        caminho = url.removeprefix(coleta.API)
        self.chamadas.append((caminho, dict(params or {})))
        if caminho == "/search/issues":
            return Resposta(corpo=self._busca(params))
        numero = int(caminho.split("/")[5])
        return Resposta(corpo=self._revisoes(numero))

    def _busca(self, params):
        q = params["q"]
        mes = q.split("merged:")[1][:7]
        com = "-commenter" not in q
        itens = []
        for numero, pr in sorted(self.prs.items()):
            if pr["mes"] != mes or pr["com_comentario"] != com:
                continue
            criado = datetime.fromisoformat(f"{mes}-10T00:00:00+00:00")
            itens.append({
                "number": numero,
                "user": {"login": f"autor{numero}", "type": pr.get("autor_tipo", "User")},
                "created_at": iso(criado),
                "pull_request": {"merged_at": iso(criado + timedelta(hours=pr["horas_merge"]))},
            })
        inicio = (params["page"] - 1) * params["per_page"]
        return {"total_count": len(itens), "items": itens[inicio:inicio + params["per_page"]]}

    def _revisoes(self, numero):
        pr = self.prs[numero]
        if pr.get("revisao_h") is None:
            return []
        criado = datetime.fromisoformat(f"{pr['mes']}-10T00:00:00+00:00")
        return [{"user": {"login": "copilot-pull-request-reviewer[bot]"}, "submitted_at": iso(criado + timedelta(hours=pr["revisao_h"]))}]


def cfg_de_teste(tmp_path, por_mes=2, janela=(date(2026, 8, 1), date(2026, 9, 30))):
    return {
        "semente": 42,
        "pasta": str(tmp_path),
        "coleta": {
            "repositorio": "org/repo", "janela": {"inicio": janela[0], "fim": janela[1]},
            "revisor": "copilot-pull-request-reviewer", "limite_revisao_horas": 1, "min_horas_ate_merge": 1,
            "por_mes": por_mes, "pausa_busca_s": 0, "saida": "prs.csv", "registro": "registro.md", "cache": "cache",
        },
    }


def prs_de_teste():
    """Por mês: 4 PRs com revisão rápida, 2 com revisão tardia, 1 de bot, 1 com merge em 30 min;
    e 6 PRs sem Copilot (um deles com revisão do Copilot escondida, que o sorteio deve trocar)."""
    prs, numero = {}, 100
    for mes in ("2026-08", "2026-09"):
        for _ in range(4):
            numero += 1
            prs[numero] = dict(mes=mes, horas_merge=20, revisao_h=0.2, com_comentario=True)
        for _ in range(2):
            numero += 1
            prs[numero] = dict(mes=mes, horas_merge=90, revisao_h=5, com_comentario=True)
        numero += 1
        prs[numero] = dict(mes=mes, horas_merge=30, revisao_h=0.1, com_comentario=True, autor_tipo="Bot")
        numero += 1
        prs[numero] = dict(mes=mes, horas_merge=0.5, revisao_h=0.1, com_comentario=True)
        for _ in range(6):
            numero += 1
            prs[numero] = dict(mes=mes, horas_merge=4, revisao_h=None, com_comentario=False)
    return prs


@pytest.fixture
def cliente(tmp_path):
    api = ApiFalsa(prs_de_teste())
    return coleta.Cliente("token", tmp_path / "cache", pausa_busca=0, sessao=api, dormir=lambda s: None), api


def test_meses_da_janela_recorta_as_pontas():
    meses = coleta.meses_da_janela(date(2026, 8, 15), date(2026, 10, 10))
    assert meses == [(date(2026, 8, 15), date(2026, 8, 31)), (date(2026, 9, 1), date(2026, 9, 30)), (date(2026, 10, 1), date(2026, 10, 10))]


def test_meses_da_janela_atravessa_o_ano():
    assert [m[0].month for m in coleta.meses_da_janela(date(2026, 11, 1), date(2027, 1, 31))] == [11, 12, 1]


def test_consulta_com_e_sem_revisor():
    com = coleta.consulta("org/repo", "bot", date(2026, 8, 1), date(2026, 8, 31), True)
    sem = coleta.consulta("org/repo", "bot", date(2026, 8, 1), date(2026, 8, 31), False)
    assert com.endswith("commenter:app/bot") and "-commenter" not in com
    assert sem.endswith("-commenter:app/bot")
    assert "merged:2026-08-01..2026-08-31" in com and "-author:app/dependabot" in com


def test_candidato_descarta_autor_bot_e_pr_sem_merge():
    item = {"number": 1, "user": {"login": "a", "type": "User"}, "created_at": "2026-08-10T00:00:00Z",
            "pull_request": {"merged_at": "2026-08-10T10:00:00Z"}}
    dados, motivo = coleta.candidato(item)
    assert motivo is None and dados["horas_ate_merge"] == 10 and dados["autor"] == "a"
    assert coleta.candidato({**item, "user": {"login": "x", "type": "Bot"}}) == (None, "autor_bot")
    assert coleta.candidato({**item, "pull_request": {"merged_at": None}}) == (None, "sem_merge")


def test_primeira_revisao_pega_a_mais_antiga_e_ignora_pendentes():
    revisoes = [
        {"user": {"login": "Copilot-Pull-Request-Reviewer[bot]"}, "submitted_at": "2026-08-10T05:00:00Z"},
        {"user": {"login": "copilot-pull-request-reviewer[bot]"}, "submitted_at": "2026-08-10T01:00:00Z"},
        {"user": {"login": "copilot-pull-request-reviewer[bot]"}, "submitted_at": None},
        {"user": {"login": "humano"}, "submitted_at": "2026-08-10T00:10:00Z"},
    ]
    assert coleta.primeira_revisao(revisoes, "copilot-pull-request-reviewer[bot]") == "2026-08-10T01:00:00Z"
    assert coleta.primeira_revisao([], "copilot-pull-request-reviewer[bot]") is None


def test_buscar_todos_junta_as_paginas(cliente, monkeypatch):
    cliente, api = cliente
    monkeypatch.setattr(coleta, "POR_PAGINA", 4)
    itens, total = coleta.buscar_todos(cliente, "repo:org/repo is:pr is:merged merged:2026-08-01..2026-08-31 -commenter:app/x")
    assert total == len(itens) == 6
    assert [p["page"] for c, p in api.chamadas] == [1, 2]
    assert len({i["number"] for i in itens}) == 6


def test_buscar_todos_recusa_resultado_incompleto(tmp_path):
    class Truncada:
        def get(self, url, params=None, headers=None, timeout=None):
            return Resposta(corpo={"total_count": 5, "items": [] if params["page"] > 1 else [{"number": 1}]})
    c = coleta.Cliente("t", tmp_path, pausa_busca=0, sessao=Truncada(), dormir=lambda s: None)
    with pytest.raises(coleta.ErroColeta, match="1 de 5"):
        coleta.buscar_todos(c, "q")


def test_buscar_todos_recusa_consulta_acima_do_teto(tmp_path):
    class Gigante:
        def get(self, url, params=None, headers=None, timeout=None):
            return Resposta(corpo={"total_count": 1500, "items": []})
    c = coleta.Cliente("t", tmp_path, pausa_busca=0, sessao=Gigante(), dormir=lambda s: None)
    with pytest.raises(coleta.ErroColeta, match="teto"):
        coleta.buscar_todos(c, "q")


def test_cache_evita_a_segunda_requisicao(cliente):
    c, api = cliente
    c.revisoes("org/repo", 101)
    c.revisoes("org/repo", 101)
    assert c.requisicoes == 1 and c.do_cache == 1
    assert len(api.chamadas) == 1


def test_espera_o_retry_after_e_tenta_de_novo(tmp_path):
    respostas = [Resposta(403, cabecalhos={"Retry-After": "7"}), Resposta(200, corpo=[])]
    dormidas = []

    class Sessao:
        def get(self, *a, **k):
            return respostas.pop(0)

    c = coleta.Cliente("t", tmp_path, pausa_busca=0, sessao=Sessao(), dormir=dormidas.append)
    assert c.revisoes("org/repo", 1) == []
    assert dormidas == [12.0]


def test_erro_http_inesperado_e_falha_depois_das_tentativas(tmp_path):
    class Sessao:
        def __init__(self, status):
            self.status = status

        def get(self, *a, **k):
            return Resposta(self.status, corpo={})

    with pytest.raises(coleta.ErroColeta, match="404"):
        coleta.Cliente("t", tmp_path / "a", sessao=Sessao(404), dormir=lambda s: None).revisoes("org/repo", 1)
    with pytest.raises(coleta.ErroColeta, match="tentativas"):
        coleta.Cliente("t", tmp_path / "b", sessao=Sessao(500), dormir=lambda s: None).revisoes("org/repo", 1)


def test_pausa_entre_buscas(tmp_path):
    tempo = [0.0]
    dormidas = []

    class Sessao:
        def get(self, *a, **k):
            return Resposta(corpo={"total_count": 0, "items": []})

    def dormir(s):
        dormidas.append(s)
        tempo[0] += s

    c = coleta.Cliente("t", tmp_path, pausa_busca=20, sessao=Sessao(), dormir=dormir, relogio=lambda: tempo[0])
    c.buscar("a")
    c.buscar("b")
    assert dormidas == [20]


def test_coletar_aplica_o_protocolo(tmp_path, cliente):
    c, _ = cliente
    df = coleta.coletar(cfg_de_teste(tmp_path), c, agora=datetime(2026, 11, 3, tzinfo=timezone.utc))
    assert list(df.columns) == coleta.COLUNAS
    assert df.groupby("grupo").size().to_dict() == {"com_bot": 4, "sem_bot": 4}
    com, sem = df[df.grupo == "com_bot"], df[df.grupo == "sem_bot"]
    assert (com["horas_ate_revisao_bot"] <= 1).all() and com["horas_ate_revisao_bot"].notna().all()
    assert sem["horas_ate_revisao_bot"].isna().all()
    assert (df["horas_ate_merge"] > 1).all()
    meses = pd.to_datetime(df["mesclado_em"]).dt.strftime("%Y-%m")
    assert (df.groupby(["grupo", meses]).size() == 2).all()
    etapas = df.attrs["registro"]["meses"]["2026-08"]
    assert etapas["com_bot"]["revisao_rapida"] == 4 and etapas["com_bot"]["revisao_tardia"] == 2
    assert etapas["com_bot"]["autor_bot"] == 1 and etapas["com_bot"]["ate_o_minimo"] == 1


def test_coletar_e_reprodutivel_e_a_semente_muda_o_sorteio(tmp_path):
    def rodar(semente, pasta):
        api = ApiFalsa(prs_de_teste())
        c = coleta.Cliente("t", pasta, pausa_busca=0, sessao=api, dormir=lambda s: None)
        return coleta.coletar({**cfg_de_teste(tmp_path), "semente": semente}, c)

    a, b = rodar(42, tmp_path / "c1"), rodar(42, tmp_path / "c2")
    pd.testing.assert_frame_equal(a, b)
    assert set(rodar(7, tmp_path / "c3")["numero_pr"]) != set(a["numero_pr"])


def test_sorteio_troca_pr_sem_bot_que_tem_revisao_do_copilot(tmp_path):
    prs = prs_de_teste()
    escondidos = [n for n, p in prs.items() if p["mes"] == "2026-08" and not p["com_comentario"]]
    for n in escondidos:   # só 2 PRs sem Copilot "limpos" em agosto; os outros 4 têm revisão
        prs[n]["revisao_h"] = 3
    for n in escondidos[:2]:
        prs[n]["revisao_h"] = None
    c = coleta.Cliente("t", tmp_path / "cache", pausa_busca=0, sessao=ApiFalsa(prs), dormir=lambda s: None)
    df = coleta.coletar(cfg_de_teste(tmp_path), c)
    sem_agosto = df[(df.grupo == "sem_bot") & (df.mesclado_em.str.startswith("2026-08"))]
    assert set(sem_agosto["numero_pr"]) == set(escondidos[:2])
    assert df.attrs["registro"]["sorteio"]["sem_bot"]["descartados"] >= 1


def test_mes_sem_pr_suficiente_e_completado_com_outro_mes(tmp_path):
    prs = prs_de_teste()
    for n, p in prs.items():
        if p["mes"] == "2026-08" and p["com_comentario"] and p.get("revisao_h") == 0.2 and n not in (101,):
            p["revisao_h"] = 5   # agosto fica com 1 revisão rápida
    c = coleta.Cliente("t", tmp_path / "cache", pausa_busca=0, sessao=ApiFalsa(prs), dormir=lambda s: None)
    df = coleta.coletar(cfg_de_teste(tmp_path), c)
    assert (df.grupo == "com_bot").sum() == 4
    sorteio = df.attrs["registro"]["sorteio"]["com_bot"]
    assert sorteio["faltas"] == {"2026-08": 1}
    assert len(sorteio["reservas"]) == 1 and sorteio["reservas"][0]["mes"] == "2026-09"


def test_salvar_e_registro(tmp_path, cliente):
    c, _ = cliente
    df = coleta.coletar(cfg_de_teste(tmp_path), c, agora=datetime(2026, 11, 3, 12, 30, tzinfo=timezone.utc))
    coleta.salvar(df, tmp_path / "saida" / "prs.csv")
    lido = pd.read_csv(tmp_path / "saida" / "prs.csv")
    assert list(lido.columns) == coleta.COLUNAS and len(lido) == 8
    coleta.escrever_registro(df, tmp_path / "saida" / "registro.md")
    texto = (tmp_path / "saida" / "registro.md").read_text(encoding="utf-8")
    assert "2026-11-03 12:30 UTC" in texto and "| 2026-08 | com_bot |" in texto and "**Total** | **4** | **4**" in texto


def test_executar_grava_csv_e_registro(tmp_path, monkeypatch, capsys):
    api = ApiFalsa(prs_de_teste())
    original = coleta.Cliente

    def com_api_falsa(token, pasta, pausa_busca=20.0, **k):
        return original(token, pasta, pausa_busca=0, sessao=api, dormir=lambda s: None)

    monkeypatch.setattr(coleta, "Cliente", com_api_falsa)
    df = coleta.executar(cfg_de_teste(tmp_path), "token")
    assert (tmp_path / "prs.csv").exists() and (tmp_path / "registro.md").exists()
    assert len(df) == 8 and "8 PRs gravados" in capsys.readouterr().out
