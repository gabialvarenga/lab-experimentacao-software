import csv
from datetime import datetime, timedelta, timezone

import pytest

from pipeline import __main__ as principal
from pipeline.cliente_http import ErroHTTP

CONFIG = """
janela:
  inicio: 2025-10-01
  fim: 2026-09-30
criterios:
  min_releases: 5
  min_workflow_runs: 50
selecao:
  alvo_aprovados: 2
  faixas_estrelas:
    - ">10000"
    - "5000..10000"
caminhos:
  cache: cache
  saida: saida
"""
BASE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def lista_releases(quantidade):
    return [
        {
            "tag_name": f"v{i}",
            "published_at": BASE + timedelta(days=i),
            "draft": False,
            "prerelease": False,
            "html_url": f"https://exemplo/v{i}",
        }
        for i in range(quantidade)
    ]


def lista_runs(conclusoes):
    return [
        {
            "id": i,
            "workflow_id": 1,
            "conclusion": conclusao,
            "created_at": BASE + timedelta(hours=i),
            "run_started_at": BASE + timedelta(hours=i),
            "updated_at": BASE + timedelta(hours=i, minutes=30),
        }
        for i, conclusao in enumerate(conclusoes)
    ]


class Mundo:
    """Substitui as funções de coleta: cada repositório é descrito por um dicionário."""

    def __init__(self):
        self.faixas = {}
        self.repos = {}
        self.faixas_buscadas = []
        self.avaliados = []
        self.configurado = None

    def repo(self, full_name, estrelas=20000, faixa=">10000", **campos):
        spec = {
            "actions": True,
            "releases": 6,
            "runs": ["success", "failure", "success"] * 20,
            "erro": None,
            "ignoradas_404": 0,
            "commits": True,
            "existe": True,
            **campos,
        }
        owner, name = full_name.split("/")
        spec["candidato"] = {
            "full_name": full_name,
            "owner": owner,
            "name": name,
            "stargazers_count": estrelas,
            "language": "Python",
            "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "default_branch": "main",
        }
        self.repos[full_name] = spec
        if faixa:
            self.faixas.setdefault(faixa, []).append(spec["candidato"])
        return spec

    def _spec(self, owner, repo, etapa):
        spec = self.repos[f"{owner}/{repo}"]
        if spec["erro"] == etapa:
            raise ErroHTTP(502)
        return spec

    def configurar(self, token, pasta_cache):
        self.configurado = (token, pasta_cache)

    def buscar_candidatos(self, faixas):
        self.faixas_buscadas.extend(faixas)
        return [c for faixa in faixas for c in self.faixas.get(faixa, [])]

    def buscar_repositorio(self, owner, repo):
        spec = self._spec(owner, repo, "repositorio")
        return spec["candidato"] if spec["existe"] else None

    def usa_actions(self, owner, repo):
        self.avaliados.append(f"{owner}/{repo}")
        return self._spec(owner, repo, "workflows")["actions"]

    def coletar_releases(self, owner, repo):
        return lista_releases(self._spec(owner, repo, "releases")["releases"])

    def coletar_runs(self, owner, repo, branch, inicio, fim):
        assert branch == "main"
        return lista_runs(self._spec(owner, repo, "runs")["runs"])

    def coletar_metadados(self, candidato, fim_janela):
        self._spec(candidato["owner"], candidato["name"], "metadados")
        return {
            "full_name": candidato["full_name"],
            "estrelas": candidato["stargazers_count"],
            "linguagem": candidato["language"],
            "contribuidores": 7,
            "idade_dias": 2464,
        }

    def releases_com_commits(self, owner, repo, releases, inicio, fim):
        spec = self._spec(owner, repo, "compare")
        return [
            {
                "tag_name": r["tag_name"],
                "published_at": r["published_at"],
                "commits": [r["published_at"] - timedelta(hours=10)] if spec["commits"] else None,
            }
            for r in releases
        ], spec["ignoradas_404"]


@pytest.fixture
def mundo(monkeypatch):
    falso = Mundo()
    monkeypatch.setenv("GITHUB_TOKEN", "token-de-teste")
    monkeypatch.setattr(principal.cliente_http, "configurar", falso.configurar)
    monkeypatch.setattr(principal.selecao, "buscar_candidatos", falso.buscar_candidatos)
    monkeypatch.setattr(principal.selecao, "buscar_repositorio", falso.buscar_repositorio)
    monkeypatch.setattr(principal.selecao, "usa_actions", falso.usa_actions)
    monkeypatch.setattr(principal.selecao, "coletar_metadados", falso.coletar_metadados)
    monkeypatch.setattr(principal.releases, "coletar_releases", falso.coletar_releases)
    monkeypatch.setattr(principal.releases, "releases_com_commits", falso.releases_com_commits)
    monkeypatch.setattr(principal.runs, "coletar_runs", falso.coletar_runs)
    return falso


@pytest.fixture
def rodar(tmp_path):
    caminho = tmp_path / "config.yaml"
    caminho.write_text(CONFIG, encoding="utf-8")

    def _rodar(*argumentos):
        return principal.main(["--config", str(caminho), *argumentos])

    return _rodar


def ler(tmp_path, nome):
    with open(tmp_path / "saida" / nome, encoding="utf-8", newline="") as arquivo:
        return list(csv.reader(arquivo))


def repositorios(tmp_path, nome="repositorios.csv"):
    cabecalho, *linhas = ler(tmp_path, nome)
    return [dict(zip(cabecalho, linha)) for linha in linhas]


def arquivo_de_repos(tmp_path, texto):
    caminho = tmp_path / "repos.txt"
    caminho.write_text(texto, encoding="utf-8")
    return str(caminho)


# execução pela busca


def test_para_no_limite_do_config_e_nao_examina_os_demais(mundo, rodar, tmp_path):
    for nome in ("o/a", "o/b", "o/c"):
        mundo.repo(nome)
    mundo.repo("o/d", estrelas=7000, faixa="5000..10000")

    assert rodar() == 0

    assert mundo.avaliados == ["o/a", "o/b"]
    assert mundo.faixas_buscadas == [">10000"]
    assert [r["full_name"] for r in repositorios(tmp_path)] == ["o/a", "o/b"]


def test_limite_da_linha_de_comando_substitui_o_do_config(mundo, rodar, tmp_path):
    for nome in ("o/a", "o/b", "o/c"):
        mundo.repo(nome)

    rodar("--limite", "1")

    assert [r["full_name"] for r in repositorios(tmp_path)] == ["o/a"]


def test_busca_a_faixa_seguinte_quando_a_anterior_nao_basta(mundo, rodar, tmp_path):
    mundo.repo("o/a")
    mundo.repo("o/b", estrelas=7000, faixa="5000..10000")

    rodar()

    assert mundo.faixas_buscadas == [">10000", "5000..10000"]
    assert [r["full_name"] for r in repositorios(tmp_path)] == ["o/a", "o/b"]


def test_repositorio_no_limite_de_duas_faixas_e_examinado_uma_vez(mundo, rodar, tmp_path):
    spec = mundo.repo("o/a", actions=False)
    mundo.faixas["5000..10000"] = [spec["candidato"]]

    rodar()

    assert mundo.avaliados == ["o/a"]
    assert ler(tmp_path, "funil.csv")[1][:3] == ["Candidatos examinados", "1", "1"]


def test_funil_tem_as_cinco_etapas_com_um_motivo_por_descarte(mundo, rodar, tmp_path):
    mundo.repo("o/sem-actions", actions=False)
    mundo.repo("o/erro", erro="runs")
    mundo.repo("o/poucas-releases", releases=4)
    mundo.repo("o/poucos-runs", runs=["success"] * 49)
    mundo.repo("o/a")
    mundo.repo("o/b")
    mundo.repo("o/nao-examinado")

    rodar()

    assert ler(tmp_path, "funil.csv") == [
        ["etapa", "entrada", "saida", "motivo"],
        ["Candidatos examinados", "7", "6", "não examinado (parada no 2º aprovado)"],
        ["Com GitHub Actions", "6", "5", "sem Actions"],
        ["Coleta sem erro", "5", "4", "erro da API"],
        ["Releases na janela", "4", "3", "menos de 5 releases"],
        ["Runs válidos na janela", "3", "2", "menos de 50 runs"],
    ]


@pytest.mark.parametrize("etapa", ["workflows", "releases", "runs", "metadados", "compare"])
def test_erro_http_em_qualquer_etapa_descarta_e_a_execucao_continua(mundo, rodar, tmp_path, etapa):
    mundo.repo("o/erro", erro=etapa)
    mundo.repo("o/a")
    mundo.repo("o/b")

    assert rodar() == 0

    assert [r["full_name"] for r in repositorios(tmp_path)] == ["o/a", "o/b"]
    assert ler(tmp_path, "funil.csv")[3] == ["Coleta sem erro", "3", "2", "erro da API"]


def test_runs_nao_sao_coletados_de_quem_falha_nas_releases(mundo, rodar, monkeypatch):
    mundo.repo("o/poucas-releases", releases=4)
    monkeypatch.setattr(principal.runs, "coletar_runs", lambda *a: pytest.fail("não deveria coletar runs"))

    assert rodar() == 0


def test_candidatos_esgotados_gravam_o_que_houver(mundo, rodar, tmp_path):
    mundo.repo("o/a")

    assert rodar() == 0

    assert len(repositorios(tmp_path)) == 1
    assert ler(tmp_path, "funil.csv")[-1][:3] == ["Runs válidos na janela", "1", "1"]


# repositorios.csv


def test_colunas_na_ordem_da_issue(mundo, rodar, tmp_path):
    mundo.repo("o/a")

    rodar("--limite", "1")

    assert ler(tmp_path, "repositorios.csv")[0] == [
        "full_name", "estrelas", "linguagem", "contribuidores", "idade_dias", "n_deploys",
        "n_runs_validos", "frequencia_semana", "lead_time_a_h", "lead_time_b_h",
        "releases_ignoradas_404", "cfr_a", "recuperacao_mediana_h", "n_episodios",
        "n_censurados_direita", "n_censurados_esquerda", "categoria_c1", "n_metricas_classificadas",
    ]  # fmt: skip


def test_metricas_do_repositorio_aprovado(mundo, rodar, tmp_path):
    mundo.repo("o/a", ignoradas_404=2)

    rodar("--limite", "1")

    assert repositorios(tmp_path)[0] == {
        "full_name": "o/a",
        "estrelas": "20000",
        "linguagem": "Python",
        "contribuidores": "7",
        "idade_dias": "2464",
        "n_deploys": "6",
        "n_runs_validos": "60",
        "frequencia_semana": repr(6 / (365 / 7)),
        "lead_time_a_h": "10.0",
        "lead_time_b_h": "10.0",
        "releases_ignoradas_404": "2",
        "cfr_a": repr(20 / 60),
        "recuperacao_mediana_h": "1.5",
        "n_episodios": "20",
        "n_censurados_direita": "0",
        "n_censurados_esquerda": "0",
        # notas: frequência 1 (Low), lead time 3, CFR 2, recuperação 3 -> mediana 2,5 -> Medium
        "categoria_c1": "Medium",
        "n_metricas_classificadas": "4",
    }


def test_metrica_indefinida_fica_vazia_e_reduz_as_classificadas(mundo, rodar, tmp_path):
    mundo.repo("o/a", runs=["success"] * 50, commits=False)

    rodar("--limite", "1")

    linha = repositorios(tmp_path)[0]
    assert linha["lead_time_a_h"] == ""
    assert linha["lead_time_b_h"] == ""
    assert linha["recuperacao_mediana_h"] == ""
    assert linha["cfr_a"] == "0.0"
    assert linha["n_metricas_classificadas"] == "2"


# --repos


def test_repos_processa_so_o_arquivo_na_ordem_dele_sem_buscar(mundo, rodar, tmp_path):
    mundo.repo("o/a", estrelas=100, faixa=None)
    mundo.repo("o/b", estrelas=900, faixa=None)
    mundo.repo("o/c", estrelas=500, faixa=None)
    mundo.repo("o/fora-do-arquivo")

    assert rodar("--repos", arquivo_de_repos(tmp_path, "o/a\n\no/b\n  o/c  \n")) == 0

    assert mundo.faixas_buscadas == []
    # o alvo_aprovados do config (2) não se aplica: os três são processados
    assert [r["full_name"] for r in repositorios(tmp_path, "repositorios_subamostra.csv")] == ["o/a", "o/b", "o/c"]
    assert ler(tmp_path, "funil_subamostra.csv")[1] == ["Candidatos examinados", "3", "3", "não examinado"]


def test_repos_nao_sobrescreve_os_csvs_da_amostra(mundo, rodar, tmp_path):
    mundo.repo("o/a", faixa=None)

    rodar("--repos", arquivo_de_repos(tmp_path, "o/a\n"))

    assert sorted(p.name for p in (tmp_path / "saida").iterdir()) == [
        "funil_subamostra.csv",
        "repositorios_subamostra.csv",
    ]


def test_repos_com_limite_explicito_para_no_limite(mundo, rodar, tmp_path):
    for nome in ("o/a", "o/b"):
        mundo.repo(nome, faixa=None)

    rodar("--repos", arquivo_de_repos(tmp_path, "o/a\no/b\n"), "--limite", "1")

    assert [r["full_name"] for r in repositorios(tmp_path, "repositorios_subamostra.csv")] == ["o/a"]


def test_repos_inexistente_entra_como_erro_da_api_e_segue(mundo, rodar, tmp_path):
    mundo.repo("o/sumiu", faixa=None, existe=False)
    mundo.repo("o/erro", faixa=None, erro="repositorio")
    mundo.repo("o/a", faixa=None)

    assert rodar("--repos", arquivo_de_repos(tmp_path, "o/sumiu\no/erro\no/a\n")) == 0

    assert [r["full_name"] for r in repositorios(tmp_path, "repositorios_subamostra.csv")] == ["o/a"]
    assert ler(tmp_path, "funil_subamostra.csv")[3] == ["Coleta sem erro", "3", "1", "erro da API"]


def test_repos_com_linha_malformada_encerra_antes_de_coletar(mundo, rodar, tmp_path, capsys):
    mundo.repo("o/a", faixa=None)

    assert rodar("--repos", arquivo_de_repos(tmp_path, "o/a\nsem-barra\n")) == 1

    assert "linha 2" in capsys.readouterr().err
    assert mundo.avaliados == []
    assert not (tmp_path / "saida").exists()


def test_repos_com_arquivo_inexistente_encerra_com_mensagem(mundo, rodar, tmp_path, capsys):
    assert rodar("--repos", str(tmp_path / "nao-existe.txt")) == 1

    assert "nao-existe.txt" in capsys.readouterr().err


# token e argumentos


def test_sem_token_encerra_com_mensagem_clara(mundo, rodar, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN")
    mundo.repo("o/a")

    assert rodar() == 1

    assert "GITHUB_TOKEN" in capsys.readouterr().err
    assert mundo.avaliados == []


def test_token_e_cache_vao_para_o_cliente_http(mundo, rodar, tmp_path):
    rodar()

    assert mundo.configurado == ("token-de-teste", str(tmp_path / "cache"))


def test_limite_que_nao_e_inteiro_positivo_e_recusado(mundo, rodar):
    with pytest.raises(SystemExit):
        rodar("--limite", "0")


def test_falha_na_busca_encerra_com_mensagem(mundo, rodar, monkeypatch, capsys):
    def busca_com_erro(faixas):
        raise ErroHTTP(503)

    monkeypatch.setattr(principal.selecao, "buscar_candidatos", busca_com_erro)

    assert rodar() == 1

    assert "busca" in capsys.readouterr().err
