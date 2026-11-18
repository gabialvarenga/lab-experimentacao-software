"""Executor sem Docker: um Docker falso devolve as saídas reais gravadas em `tests/dados/`."""

import csv
import shutil
import sys
from pathlib import Path

import pytest

from lab05 import config, executor

DADOS = Path(__file__).parent / "dados"


@pytest.fixture
def cfg(tmp_path):
    """O config real do Lab05, com 2 repetições e a saída numa pasta temporária."""
    c = config.carregar()
    shutil.copy(Path(c["pasta"]) / "config.yaml", tmp_path / "config.yaml")
    c["pasta"] = str(tmp_path)
    return executor.aplicar_ajustes(c, repeticoes=2, saida="brutos")


class DockerFalso:
    """Imita `executor.Docker`: grava o JSON do cliente na pasta de saídas e registra as chamadas."""

    def __init__(self, pasta_saidas, falhar=None, sem_json=False):
        self.pasta_saidas = Path(pasta_saidas)
        self.falhar = falhar or {}  # (etapa, execucao) -> mensagem
        self.sem_json = sem_json
        self.chamadas = []
        self.atual = None

    def _talvez_falhar(self, etapa):
        if (etapa, self.atual) in self.falhar:
            raise executor.ErroExecucao(self.falhar[(etapa, self.atual)])

    def limpar(self):
        self.chamadas.append(("limpar",))

    def subir(self, servidor, io_threads, limite_s):
        self.atual = (servidor, io_threads)
        self.chamadas.append(("subir", servidor, io_threads))
        self._talvez_falhar("subir")

    def info(self, servidor, secao):
        self.chamadas.append(("info", servidor, secao))
        texto = (DADOS / f"info-{secao}-{servidor}.txt").read_text(encoding="utf-8")
        return executor.leitura.ler_info(texto)

    def cliente(self, argumentos, timeout):
        self.chamadas.append(("cliente", argumentos))
        destino = [a for a in argumentos if a.startswith("--json-out-file=")]
        if destino:
            self._talvez_falhar("medir")
            if not self.sem_json:
                nome = destino[0].split("/")[-1]
                shutil.copy(DADOS / "redis-t1-set-r01.json", self.pasta_saidas / nome)

    def parar(self, servidor):
        self.chamadas.append(("parar", servidor))
        self._talvez_falhar("parar")


def _relogio():
    instantes = iter(f"2026-11-18T10:{m // 60:02d}:{m % 60:02d}-03:00" for m in range(10_000))
    return lambda: next(instantes)


def _rodar(cfg, docker, **kw):
    return executor.executar(
        cfg, docker=docker, agora=_relogio(), dormir=lambda s: None, coletar_ambiente=lambda: {"Item": "valor"}, log=lambda m: None, **kw
    )


def _ler_csv(caminho):
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def _saidas(cfg):
    return Path(cfg["pasta"]) / cfg["saida"] / "saidas"


# --------------------------------------------------------------------------- plano


def test_plano_completo_do_config_tem_360_execucoes_em_blocos(cfg):
    plano = executor.gerar_plano(executor.aplicar_ajustes(cfg, repeticoes=30))
    assert len(plano) == 360
    assert [ex.ordem for ex in plano] == list(range(1, 361))
    assert len({ex.execucao_id for ex in plano}) == 360
    for bloco in range(30):
        execucoes = plano[bloco * 12 : (bloco + 1) * 12]
        assert {ex.repeticao for ex in execucoes} == {bloco + 1}
        assert len({(ex.servidor, ex.io_threads, ex.carga) for ex in execucoes}) == 12


def test_plano_e_reproduzivel_pela_semente(cfg):
    assert executor.gerar_plano(cfg) == executor.gerar_plano(cfg)
    outra = executor.gerar_plano({**cfg, "semente": 7})
    assert [ex.execucao_id for ex in outra] != [ex.execucao_id for ex in executor.gerar_plano(cfg)]


def test_plano_com_a_semente_42_comeca_sempre_igual(cfg):
    primeiras = [ex.execucao_id for ex in executor.gerar_plano(cfg)[:3]]
    assert primeiras == ["redis-t1-set-r01", "valkey-t1-get-r01", "valkey-t1-set-r01"]


def test_ordem_e_sorteada_dentro_dos_blocos(cfg):
    plano = executor.gerar_plano(cfg)
    assert [ex.execucao_id[:-4] for ex in plano[:12]] != [ex.execucao_id[:-4] for ex in plano[12:]]


def test_plano_sem_repeticoes_e_recusado(cfg):
    with pytest.raises(ValueError, match="repetição"):
        executor.gerar_plano(executor.aplicar_ajustes(cfg, repeticoes=0))


# --------------------------------------------------------------------------- argumentos do cliente


def test_argumentos_da_medicao_seguem_o_protocolo(cfg):
    argumentos = executor.argumentos_carga(cfg, "valkey", "misto", 30, "/saidas/x.json")
    for esperado in ["--server=valkey", "-t", "4", "-c", "12", "-d", "100", "--pipeline=1", "--ratio=1:4",
                     "--key-pattern=R:R", "--key-maximum=100000", "--test-time=30",
                     "--print-percentiles=50,99", "--json-out-file=/saidas/x.json"]:  # fmt: skip
        assert esperado in argumentos


def test_aquecimento_nao_grava_json(cfg):
    argumentos = executor.argumentos_carga(cfg, "redis", "set", 10)
    assert "--ratio=1:0" in argumentos and "--test-time=10" in argumentos
    assert not any(a.startswith("--json-out-file") for a in argumentos)


def test_precarga_grava_todas_as_chaves_em_sequencia(cfg):
    argumentos = executor.argumentos_precarga(cfg, "redis")
    assert {"--ratio=1:0", "--key-pattern=P:P", "allkeys", "--key-maximum=100000"} <= set(argumentos)


# --------------------------------------------------------------------------- plano inteiro


def test_executar_roda_o_plano_inteiro_e_grava_o_csv_congelado(cfg):
    docker = DockerFalso(_saidas(cfg))
    resumo = _rodar(cfg, docker)
    linhas = _ler_csv(Path(cfg["pasta"]) / "brutos" / "execucoes.csv")
    assert resumo["concluidas"] == len(linhas) == 24 and not resumo["falhas"]
    assert list(linhas[0]) == executor.COLUNAS
    assert [int(l["ordem"]) for l in linhas] == list(range(1, 25))
    assert [l["execucao_id"] for l in linhas] == [ex.execucao_id for ex in executor.gerar_plano(cfg)]
    redis = next(l for l in linhas if l["servidor"] == "redis")
    valkey = next(l for l in linhas if l["servidor"] == "valkey")
    assert (redis["versao"], valkey["versao"]) == ("8.10.3", "9.1.3")
    assert redis["ops_s"] == "68107.4" and redis["lat_p50_ms"] == "0.679" and redis["lat_p99_ms"] == "1.415"
    assert redis["memoria_bytes"] == "1446064" and valkey["memoria_bytes"] == "994248"
    assert redis["inicio"] < redis["fim"]
    assert docker.chamadas[0] == ("limpar",)
    assert sum(1 for c in docker.chamadas if c[0] == "parar") == 24


def test_executar_grava_o_registro_com_ambiente_e_resumo(cfg):
    _rodar(cfg, DockerFalso(_saidas(cfg)))
    registro = (Path(cfg["pasta"]) / "brutos" / "registro-2026-11-18.md").read_text(encoding="utf-8")
    assert registro.startswith("# Registro da execução do benchmark — 2026-11-18")
    assert "| Item | valor |" in registro
    assert "Semente: 42" in registro and "Concluídas nesta sessão: 24" in registro


def test_falha_e_registrada_sem_valor_inventado_e_a_coleta_segue(cfg):
    falhar = {("subir", ("valkey", 4)): "o contêiner não ficou pronto", ("medir", ("redis", 1)): "cliente caiu"}
    docker = DockerFalso(_saidas(cfg), falhar=falhar)
    resumo = _rodar(cfg, docker)
    linhas = _ler_csv(Path(cfg["pasta"]) / "brutos" / "execucoes.csv")
    falhas = _ler_csv(Path(cfg["pasta"]) / "brutos" / "falhas.csv")
    assert len(linhas) == 24 - 12 and resumo["concluidas"] == 12
    assert not any((l["servidor"], l["io_threads"]) in {("valkey", "4"), ("redis", "1")} for l in linhas)
    assert {f["etapa"] for f in falhas} == {"subida", "medicao"} and len(falhas) == 12
    assert all(f["inicio"] and f["fim"] for f in falhas)
    assert all(v != "" for l in linhas for v in l.values())
    assert sum(1 for c in docker.chamadas if c[0] == "parar") == 24  # o contêiner para mesmo com falha
    registro = next((Path(cfg["pasta"]) / "brutos").glob("registro-*.md")).read_text(encoding="utf-8")
    assert "Falhas nesta sessão: 12 (detalhes em `falhas.csv`)" in registro


def test_cliente_sem_json_vira_falha_de_leitura(cfg):
    resumo = _rodar(cfg, DockerFalso(_saidas(cfg), sem_json=True))
    assert resumo["concluidas"] == 0
    assert {etapa for _, etapa, _ in resumo["falhas"]} == {"leitura"}


def test_falha_ao_parar_so_avisa(cfg):
    falhar = {("parar", ("redis", 1)): "não parou"}
    mensagens = []
    resumo = executor.executar(
        cfg, docker=DockerFalso(_saidas(cfg), falhar=falhar), agora=_relogio(), dormir=lambda s: None,
        coletar_ambiente=dict, log=mensagens.append,
    )  # fmt: skip
    assert resumo["concluidas"] == 24
    assert any("não parou" in m for m in mensagens)


def test_retomada_nao_repete_execucoes_gravadas_e_tenta_de_novo_as_que_falharam(cfg):
    falhar = {("subir", ("valkey", 1)): "falhou"}
    _rodar(cfg, DockerFalso(_saidas(cfg), falhar=falhar))
    docker = DockerFalso(_saidas(cfg))
    resumo = _rodar(cfg, docker)
    subidas = [c[1:] for c in docker.chamadas if c[0] == "subir"]
    assert resumo["ja_gravadas"] == 18 and resumo["concluidas"] == 6
    assert set(subidas) == {("valkey", 1)}
    linhas = _ler_csv(Path(cfg["pasta"]) / "brutos" / "execucoes.csv")
    assert len(linhas) == len({l["execucao_id"] for l in linhas}) == 24


def test_retomada_sem_pendentes_nao_chama_o_docker(cfg):
    _rodar(cfg, DockerFalso(_saidas(cfg)))
    docker = DockerFalso(_saidas(cfg))
    resumo = _rodar(cfg, docker)
    assert docker.chamadas == [] and resumo["concluidas"] == 0 and resumo["ja_gravadas"] == 24


def test_interrupcao_guarda_o_que_terminou_e_permite_retomar(cfg):
    class Interrompe(DockerFalso):
        def subir(self, servidor, io_threads, limite_s):
            if sum(1 for c in self.chamadas if c[0] == "subir") == 5:
                raise KeyboardInterrupt
            super().subir(servidor, io_threads, limite_s)

    resumo = _rodar(cfg, Interrompe(_saidas(cfg)))
    assert resumo["interrompida"] and resumo["concluidas"] == 5
    registro = next((Path(cfg["pasta"]) / "brutos").glob("registro-*.md")).read_text(encoding="utf-8")
    assert "interrompida" in registro
    resumo = _rodar(cfg, DockerFalso(_saidas(cfg)))
    assert resumo["ja_gravadas"] == 5 and resumo["concluidas"] == 19
    registro = next((Path(cfg["pasta"]) / "brutos").glob("registro-*.md")).read_text(encoding="utf-8")
    assert registro.count("## Sessão iniciada em") == 2


def test_retomada_com_config_diferente_e_recusada(cfg):
    _rodar(cfg, DockerFalso(_saidas(cfg)))
    with pytest.raises(executor.ErroPlano, match="config mudou"):
        _rodar({**cfg, "semente": 7}, DockerFalso(_saidas(cfg)))


def test_csv_com_outras_colunas_e_recusado(cfg):
    pasta = Path(cfg["pasta"]) / "brutos"
    pasta.mkdir()
    (pasta / "execucoes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(executor.ErroPlano, match="colunas"):
        _rodar(cfg, DockerFalso(_saidas(cfg)))


def test_aplicar_ajustes_nao_altera_o_config_original(cfg):
    novo = executor.aplicar_ajustes(cfg, aquecimento_s=1, medicao_s=2, pausa_s=0)
    assert (novo["cliente"]["aquecimento_s"], novo["cliente"]["medicao_s"], novo["cliente"]["pausa_s"]) == (1, 2, 0)
    assert (cfg["cliente"]["aquecimento_s"], cfg["cliente"]["medicao_s"]) == (10, 30)


# --------------------------------------------------------------------------- comandos do Docker


class RodarFalso:
    def __init__(self, respostas=None):
        self.respostas = respostas or {}
        self.comandos = []

    def __call__(self, comando, cwd=None, env=None, timeout=None):
        self.comandos.append((comando, cwd, env, timeout))
        for trecho, resposta in self.respostas.items():
            if trecho in comando:
                return resposta
        return 0, "ok"


def _docker(tmp_path, rodar):
    servidores = config.carregar()["plano"]["servidores"]
    return executor.Docker(tmp_path, tmp_path / "saidas", servidores, rodar=rodar)


def test_docker_sobe_com_o_tratamento_e_a_pasta_de_saidas(tmp_path):
    rodar = RodarFalso()
    _docker(tmp_path, rodar).subir("valkey", 4, 90)
    comando, cwd, env, timeout = rodar.comandos[0]
    assert comando == ["docker", "compose", "--profile", "valkey", "up", "-d", "--wait", "--wait-timeout", "90", "valkey"]
    assert cwd == str(tmp_path) and env["IO_THREADS"] == "4" and timeout == 150
    assert env["SAIDAS"] == str((tmp_path / "saidas").resolve())


def test_docker_info_usa_o_cli_de_cada_servidor(tmp_path):
    texto = (DADOS / "info-server-valkey.txt").read_text(encoding="utf-8")
    rodar = RodarFalso({"exec": (0, texto)})
    info = _docker(tmp_path, rodar).info("valkey", "server")
    assert rodar.comandos[0][0][-5:] == ["-T", "valkey", "valkey-cli", "INFO", "server"]
    assert info["valkey_version"] == "9.1.3"


def test_docker_cliente_limpar_e_parar(tmp_path):
    rodar = RodarFalso()
    docker = _docker(tmp_path, rodar)
    docker.cliente(["--server=redis"], timeout=10)
    docker.limpar()
    docker.parar("redis")
    assert rodar.comandos[0][0][2:] == ["--profile", "cliente", "run", "--rm", "cliente", "--server=redis"]
    assert rodar.comandos[1][0] == ["docker", "compose", "--profile", "redis", "--profile", "valkey",
                                   "--profile", "cliente", "down", "--remove-orphans"]  # fmt: skip
    assert rodar.comandos[2][0][-1] == "down"


@pytest.mark.parametrize("resposta, mensagem", [((1, "erro 1\nerro final\n"), "erro final"), ((124, ""), "sem saída")])
def test_docker_com_erro_levanta_erro_execucao(tmp_path, resposta, mensagem):
    with pytest.raises(executor.ErroExecucao, match=mensagem):
        _docker(tmp_path, RodarFalso({"up": resposta})).subir("redis", 1, 10)


def test_rodar_comando_devolve_codigo_e_saida():
    codigo, saida = executor.rodar_comando([sys.executable, "-c", "print('ok')"])
    assert codigo == 0 and "ok" in saida


def test_rodar_comando_inexistente_e_tempo_esgotado():
    assert executor.rodar_comando(["comando-que-nao-existe-lab05"])[0] == 127
    assert executor.rodar_comando([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.5)[0] == 124
