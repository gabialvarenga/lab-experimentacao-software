"""Testes dos gráficos G1 a G4 e da exportação (S02-05)."""

import pandas as pd
import pytest
from plotly import graph_objects as go

from lab05 import graficos
from lab05.descritiva import METRICAS
from tests.conftest import coleta_sintetica


@pytest.fixture
def coleta() -> pd.DataFrame:
    df = coleta_sintetica(n=6, razao=1.2, sigma=0.05, semente=1)
    df["execucao_id"] = [f"{s}-t{t}-{c}-r{r:02d}" for s, t, c, r in zip(df.servidor, df.io_threads, df.carga, df.repeticao)]
    return df


@pytest.fixture
def comparacoes() -> pd.DataFrame:
    linhas = []
    for metrica in METRICAS:
        for threads in (1, 4):
            for carga in ("get", "misto", "set"):
                razao = 1.2 if threads == 4 else 1.0
                linhas.append({"metrica": metrica, "io_threads": threads, "carga": carga, "razao_medianas": razao,
                               "ic_inf": razao * 0.9, "ic_sup": razao * 1.1, "p_holm": 0.01 if threads == 4 else 0.5,
                               "situacao": "diferença relevante" if threads == 4 else "inconclusivo"})
    return pd.DataFrame(linhas)


def _cores(figura: go.Figure) -> dict:
    """Nome do traço -> cor, só dos traços de servidor."""
    cores = {}
    for traco in figura.data:
        if traco.name in graficos.NOMES_SERVIDOR.values():
            cor = traco.marker.color if traco.marker.color else None
            if isinstance(traco, go.Scatter) and traco.mode and "lines" in traco.mode:
                cor = traco.line.color
            cores.setdefault(traco.name, set()).add(cor)
    return cores


def test_g1_barras_com_mediana_e_rotulo(coleta):
    figura = graficos.g1(coleta)
    assert isinstance(figura, go.Figure)
    barras = [t for t in figura.data if isinstance(t, go.Bar)]
    assert len(barras) == 2 * len(METRICAS)
    assert {t.name for t in barras} == set(graficos.NOMES_SERVIDOR.values())
    assert sum(t.showlegend for t in barras) == 2   # legenda só uma vez por servidor
    assert all(len(t.y) == 6 and all(t.text) for t in barras)
    redis_ops = barras[0]
    esperado = coleta[(coleta.servidor == "redis") & (coleta.io_threads == 1) & (coleta.carga == "set")]["ops_s"].median()
    assert redis_ops.y[0] == pytest.approx(esperado)
    assert figura.layout.title.text == graficos.TITULOS["g1"]


def test_g1_razao_valkey_redis_anotada(coleta):
    figura = graficos.g1(coleta, metricas=["ops_s"])
    textos = [a.text for a in figura.layout.annotations if a.text.startswith("V÷R")]
    assert len(textos) == 6


def test_g1_memoria_em_mib(coleta):
    figura = graficos.g1(coleta, metricas=["memoria_bytes"])
    valores = [v for t in figura.data for v in t.y]
    assert max(valores) < coleta["memoria_bytes"].max() / 1000   # convertido para MiB


def test_g2_mediana_relativa_por_bloco(coleta):
    figura = graficos.g2(coleta)
    linhas = [t for t in figura.data if t.name == "Mediana do bloco"]
    assert len(linhas) == len(graficos.METRICAS_DERIVA)
    assert list(linhas[0].x) == sorted(coleta["repeticao"].unique())
    rel = graficos.relativos(coleta, "ops_s")
    assert rel.groupby([coleta.servidor, coleta.io_threads, coleta.carga]).median().round(9).eq(1).all()


def test_g3_veredito_e_ic(comparacoes):
    figura = graficos.g3(comparacoes)
    pontos = [t for t in figura.data if isinstance(t, go.Scatter)]
    # 4 threads: relevante com razão 1,2 -> Valkey melhor na vazão e Redis melhor nas demais; 1 thread: inconclusivo
    assert {t.name for t in pontos} == {"Valkey melhor", "Redis melhor", "Inconclusivo"}
    for traco in pontos:
        assert all(abs(a - 0.1 * x) < 1e-9 for a, x in zip(traco.error_x.array, traco.x))
        assert all(t.endswith("×") for t in traco.text)
    eixo = figura.layout.xaxis
    assert eixo.type == "log"
    assert 10 ** eixo.range[0] <= comparacoes["ic_inf"].min()   # o IC nunca é cortado
    assert 10 ** eixo.range[1] >= comparacoes["ic_sup"].max()
    lados = [a.text for a in figura.layout.annotations if "melhor" in a.text]
    assert "<b>Valkey melhor →</b>" in lados and "<b>← Valkey melhor</b>" in lados   # o lado muda com a métrica


@pytest.mark.parametrize("metrica, razao, situacao, esperado", [
    ("ops_s", 1.6, "diferença relevante", "Valkey melhor"),
    ("ops_s", 0.8, "diferença relevante", "Redis melhor"),
    ("lat_p99_ms", 0.6, "diferença relevante", "Valkey melhor"),
    ("memoria_bytes", 1.2, "diferença relevante", "Redis melhor"),
    ("lat_p50_ms", 1.01, "diferença pequena demais", "Empate na prática (diferença < 5%)"),
    ("lat_p99_ms", 1.0, "equivalência prática", "Empate na prática (diferença < 5%)"),
    ("ops_s", 1.1, "inconclusivo", "Inconclusivo"),
])
def test_veredito(metrica, razao, situacao, esperado):
    assert graficos.veredito(metrica, razao, situacao) == esperado


def test_g3_recusa_tabela_sem_colunas(comparacoes):
    with pytest.raises(ValueError, match="ic_sup"):
        graficos.g3(comparacoes.drop(columns="ic_sup"))


def test_g4_uma_linha_por_servidor_carga_e_metrica(coleta):
    figura = graficos.g4(coleta)
    linhas = [t for t in figura.data if isinstance(t, go.Scatter)]
    assert len(linhas) == 2 * len(graficos.CARGAS) * len(graficos.METRICAS_Q3)
    assert all(len(t.x) == 2 for t in linhas)
    assert figura.layout.yaxis.type == "log"


def test_mesma_cor_por_servidor_em_todas(coleta, comparacoes):
    for figura in (graficos.g1(coleta), graficos.g2(coleta), graficos.g4(coleta)):
        for servidor, nome in graficos.NOMES_SERVIDOR.items():
            assert _cores(figura)[nome] == {graficos.CORES_SERVIDOR[servidor]}


def test_exportar_grava_figuras_e_pagina(coleta, comparacoes, tmp_path):
    caminhos = graficos.exportar(coleta, comparacoes, tmp_path / "figuras", "Teste", "brutos/execucoes.csv")
    assert [c.name for c in caminhos] == ["g1.html", "g2.html", "g3.html", "g4.html", "apresentacao.html"]
    pagina = (tmp_path / "figuras" / "apresentacao.html").read_text(encoding="utf-8")
    for nome in graficos.FIGURAS:
        assert f'id="{nome}"' in pagina
    assert "Como ler." in pagina
    assert pagina.count("<script type=\"text/javascript\">/**") <= 1   # Plotly.js embutido uma vez só


def test_textos_de_leitura_existem():
    for nome in graficos.FIGURAS:
        frases = [f for f in graficos.TEXTOS[nome].split(". ") if f]
        assert 2 <= len(frases) <= 5
