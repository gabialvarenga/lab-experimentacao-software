from pathlib import Path

from rodar_analise_completa import (
    PASSOS,
    Passo,
    ResultadoPasso,
    avisos_de_versao,
    executar_pipeline,
    formatar_arquivo_resultados,
    montar_comando,
    normalizar_saida,
    selecionar_passos,
)


def _ids(passos):
    return [p.id for p in passos]


def test_ordem_dos_passos_respeita_dependencias_de_dados():
    assert _ids(PASSOS) == ["contagem", "metricas", "rq1_rq2", "rq3", "dashboard"]


def test_selecionar_passos_sem_flag_devolve_todos():
    assert selecionar_passos(pular_metricas=False) == PASSOS


def test_selecionar_passos_pular_metricas_mantem_a_ordem_dos_demais():
    assert _ids(selecionar_passos(pular_metricas=True)) == [
        "contagem",
        "rq1_rq2",
        "rq3",
        "dashboard",
    ]


def test_montar_comando_usa_o_python_informado_e_os_argumentos_do_passo():
    comando = montar_comando(PASSOS[0], python="py")
    assert comando[0] == "py"
    assert Path(comando[1]).name == "contagem_testes.py"
    assert comando[2:] == ["--lote"]


def test_normalizar_saida_troca_caminho_absoluto_e_crlf():
    raiz = Path("C:/Users/alguem/repo")
    texto = f"Graficos salvos em {raiz / 'lab02' / 'analise'}\r\nfim\r\n"
    assert normalizar_saida(texto, raiz) == "Graficos salvos em <repo>/lab02/analise\nfim\n"


def test_avisos_de_versao_aponta_divergencia_do_que_foi_travado():
    avisos = avisos_de_versao({"radon": "6.0.1", "jscpd": "5.3.2"})
    assert len(avisos) == 1
    assert "jscpd" in avisos[0] and "5.2.0" in avisos[0]


def test_avisos_de_versao_vazio_quando_bate_com_o_travado():
    assert avisos_de_versao({"radon": "6.0.1", "jscpd": "5.2.0"}) == []


def test_avisos_de_versao_ignora_ferramenta_sem_versao_detectada():
    assert avisos_de_versao({"radon": "6.0.1"}) == []


def test_executar_pipeline_para_no_primeiro_passo_que_falha():
    chamados = []

    def executar(passo):
        chamados.append(passo.id)
        codigo = 3 if passo.id == "metricas" else 0
        return ResultadoPasso(codigo, "saida", 0.1)

    codigo, _ = executar_pipeline(PASSOS, executar, imprimir=lambda _: None)

    assert codigo == 1
    assert chamados == ["contagem", "metricas"]


def test_executar_pipeline_coleta_saida_so_dos_passos_que_pedem_salvar():
    def executar(passo):
        return ResultadoPasso(0, f"saida de {passo.id}", 0.1)

    codigo, coletadas = executar_pipeline(PASSOS, executar, imprimir=lambda _: None)

    assert codigo == 0
    assert [(p.id, s) for p, s in coletadas] == [
        ("rq1_rq2", "saida de rq1_rq2"),
        ("rq3", "saida de rq3"),
    ]


def test_formatar_arquivo_resultados_tem_uma_secao_por_passo():
    passo = Passo("x", "Passo X", "analise/x.py", salvar_saida=True)
    texto = formatar_arquivo_resultados([(passo, "linha 1\nlinha 2\n")])
    assert "## analise/x.py" in texto
    assert "linha 1\nlinha 2" in texto
