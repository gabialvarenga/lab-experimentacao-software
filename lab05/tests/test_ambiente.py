import sys
from pathlib import Path

from lab05 import ambiente, config


def test_decodificar_utf8_e_utf16_do_wsl():
    assert ambiente.decodificar("versão 2".encode("utf-8")) == "versão 2"
    assert ambiente.decodificar("﻿Versão do WSL: 2.6.3.0".encode("utf-16-le")) == "Versão do WSL: 2.6.3.0"
    assert ambiente.decodificar(b"") == ""


def test_rodar_devolve_indisponivel_quando_falha():
    assert ambiente._rodar([sys.executable, "-c", "print('ok')"]) == "ok"
    assert ambiente._rodar([sys.executable, "-c", "import sys; sys.exit(3)"]) == ambiente.INDISPONIVEL
    assert ambiente._rodar(["comando-que-nao-existe-lab05"]) == ambiente.INDISPONIVEL


def _rodar_falso(comando, cwd=None):
    if comando[:2] == ["docker", "compose"] and "--images" in comando:
        return "redis:8.10.3@sha256:aaa\nvalkey/valkey:9.1.3@sha256:bbb"
    if comando[:3] == ["docker", "image", "inspect"]:
        return "sha256:id-" + comando[3].split(":")[0]
    if comando[0] == "wsl":
        return "Versão do WSL: 2.6.3.0\nVersão do kernel: 6.6.87.2-1"
    return f"saída de {comando[0]}"


def test_coletar_no_windows(tmp_path):
    (tmp_path / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    amb = ambiente.coletar(tmp_path, rodar=_rodar_falso, sistema="win32")
    assert amb["imagens"] == [
        ("redis:8.10.3@sha256:aaa", "sha256:id-redis"),
        ("valkey/valkey:9.1.3@sha256:bbb", "sha256:id-valkey/valkey"),
    ]
    assert amb["WSL"] == "Versão do WSL: 2.6.3.0 ; Versão do kernel: 6.6.87.2-1"
    assert amb["Plano de energia"] == "saída de powercfg"
    assert amb["Processador"] == "saída de powershell"
    assert "GiB" in amb["Memória da máquina"]
    assert len(amb["SHA-256 do compose.yaml"]) == 64


def test_coletar_fora_do_windows_e_sem_docker(tmp_path):
    amb = ambiente.coletar(tmp_path, rodar=lambda comando, cwd=None: ambiente.INDISPONIVEL, sistema="linux")
    assert amb["imagens"] == []
    assert amb["WSL"] == amb["Plano de energia"] == "não se aplica"
    assert amb["SHA-256 do compose.yaml"] == ambiente.INDISPONIVEL
    assert amb["Processador"]


def test_wslconfig(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert "sem .wslconfig" in ambiente._wslconfig()
    (tmp_path / ".wslconfig").write_text("[wsl2]\nmemory=11GB\nprocessors = 8\nswap=0\nguiApplications=false\n", encoding="utf-8")
    assert ambiente._wslconfig() == "memory=11GB; processors = 8; swap=0"
    (tmp_path / ".wslconfig").write_text("[wsl2]\n", encoding="utf-8")
    assert ambiente._wslconfig() == "sem limites no .wslconfig"


def _resumo(**mudancas):
    return {"inicio": "2026-11-18T10:00:00-03:00", "fim": "2026-11-18T11:00:00-03:00", "plano": 12, "ja_gravadas": 0,
            "pendentes": 12, "concluidas": 11, "falhas": [("redis-t1-set-r01", "subida", "não subiu")],
            "interrompida": False, **mudancas}  # fmt: skip


def test_registro_tem_ambiente_imagens_plano_e_resumo(tmp_path):
    caminho = tmp_path / "registro-2026-11-18.md"
    amb = {"Docker (cliente / servidor)": "29.3.1 | 29.3.1", "imagens": [("redis:8.10.3@sha256:aaa", "sha256:id")]}
    cfg = config.carregar()
    ambiente.escrever_registro(caminho, amb, cfg, _resumo())
    ambiente.anexar_resumo(caminho, _resumo())
    texto = caminho.read_text(encoding="utf-8")
    assert texto.startswith("# Registro da execução do benchmark — 2026-11-18")
    assert "| Docker (cliente / servidor) | 29.3.1 / 29.3.1 |" in texto
    assert "| `redis:8.10.3@sha256:aaa` | `sha256:id` |" in texto
    assert "Semente: 42" in texto and f"repetições: {cfg['plano']['repeticoes']}" in texto
    assert "`redis-t1-set-r01`, etapa subida: não subiu" in texto


def test_registro_de_segunda_sessao_no_mesmo_dia_acrescenta_secao(tmp_path):
    caminho = tmp_path / "registro.md"
    cfg = {**config.carregar(), "pasta": str(tmp_path)}  # sem config.yaml na pasta: SHA indisponível
    for _ in range(2):
        ambiente.escrever_registro(caminho, {}, cfg, _resumo())
        ambiente.anexar_resumo(caminho, _resumo(interrompida=True, falhas=[]))
    texto = caminho.read_text(encoding="utf-8")
    assert texto.count("# Registro da execução") == 1 and texto.count("## Sessão iniciada") == 2
    assert "| indisponível | |" in texto and "SHA-256 do config.yaml: `indisponível`" in texto
    assert "(interrompida; retomar com o mesmo comando)" in texto


def test_modo_de_energia_e_alimentacao_no_windows():
    def rodar(comando, cwd=None):
        texto = comando[-1]
        if "ActiveOverlayAcPowerScheme" in texto:
            return "DED574B5-45A0-4F42-8737-46345C09C238"
        return "2"

    assert ambiente._modo_energia(rodar) == "Melhor desempenho (DED574B5-45A0-4F42-8737-46345C09C238)"
    assert ambiente._alimentacao(rodar) == "tomada (BatteryStatus 2)"
    assert ambiente._alimentacao(lambda c, cwd=None: "1") == "bateria (descarregando) (BatteryStatus 1)"
    indisponivel = lambda c, cwd=None: ambiente.INDISPONIVEL  # noqa: E731
    assert ambiente._modo_energia(indisponivel) == ambiente.INDISPONIVEL
    assert ambiente._alimentacao(indisponivel) == "sem bateria ou indisponível"
