"""Leitura do `config.yaml` e do token do GitHub.

É o único módulo que lê o arquivo de configuração e a variável de ambiente
`GITHUB_TOKEN`; os demais recebem os valores como parâmetros. O token nunca é escrito em
arquivo nem em log.
"""

import os
from datetime import date, datetime

import yaml

VARIAVEL_DO_TOKEN = "GITHUB_TOKEN"


class ErroDeConfiguracao(Exception):
    """Configuração ausente ou inválida; a mensagem diz o que corrigir."""


def carregar(caminho: str) -> dict:
    """Conteúdo do `config.yaml`, com a janela em `date` e o token em `config["token"]`.

    Caminhos relativos de `caminhos` são resolvidos a partir da pasta do arquivo de
    configuração. Levanta `ErroDeConfiguracao` se o arquivo, uma chave obrigatória ou o
    token estiverem ausentes.
    """
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            config = yaml.safe_load(arquivo)
    except OSError as erro:
        raise ErroDeConfiguracao(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    except yaml.YAMLError as erro:
        raise ErroDeConfiguracao(f"{caminho} não é um YAML válido: {erro}") from erro
    if not isinstance(config, dict):
        raise ErroDeConfiguracao(f"{caminho} está vazio ou não é um mapeamento")

    janela = _secao(config, "janela")
    janela["inicio"] = _data(_valor(janela, "janela", "inicio"))
    janela["fim"] = _data(_valor(janela, "janela", "fim"))
    if janela["fim"] < janela["inicio"]:
        raise ErroDeConfiguracao("janela.fim não pode ser anterior a janela.inicio")

    criterios = _secao(config, "criterios")
    _inteiro_positivo(criterios, "criterios", "min_releases")
    _inteiro_positivo(criterios, "criterios", "min_workflow_runs")

    selecao = _secao(config, "selecao")
    _inteiro_positivo(selecao, "selecao", "alvo_aprovados")
    faixas = _valor(selecao, "selecao", "faixas_estrelas")
    if not isinstance(faixas, list) or not faixas:
        raise ErroDeConfiguracao("selecao.faixas_estrelas deve ser uma lista com ao menos uma faixa")
    selecao["faixas_estrelas"] = [str(faixa) for faixa in faixas]

    caminhos = _secao(config, "caminhos")
    pasta = os.path.dirname(os.path.abspath(caminho))
    for nome in ("cache", "saida"):
        caminhos[nome] = os.path.normpath(os.path.join(pasta, str(_valor(caminhos, "caminhos", nome))))

    config["token"] = _token()
    return config


def _token() -> str:
    token = os.environ.get(VARIAVEL_DO_TOKEN, "").strip()
    if not token:
        raise ErroDeConfiguracao(
            f"a variável de ambiente {VARIAVEL_DO_TOKEN} não está definida. Defina-a com um token "
            f'pessoal do GitHub: $env:{VARIAVEL_DO_TOKEN} = "<token>" (PowerShell) ou '
            f"export {VARIAVEL_DO_TOKEN}=<token> (Linux/macOS)"
        )
    return token


def _secao(config: dict, nome: str) -> dict:
    secao = config.get(nome)
    if not isinstance(secao, dict):
        raise ErroDeConfiguracao(f"seção obrigatória ausente no config: {nome}")
    return secao


def _valor(secao: dict, nome_secao: str, chave: str):
    if secao.get(chave) is None:
        raise ErroDeConfiguracao(f"chave obrigatória ausente no config: {nome_secao}.{chave}")
    return secao[chave]


def _inteiro_positivo(secao: dict, nome_secao: str, chave: str) -> None:
    valor = _valor(secao, nome_secao, chave)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErroDeConfiguracao(f"{nome_secao}.{chave} deve ser um inteiro positivo")


def _data(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ErroDeConfiguracao(f"data inválida no config: {valor!r} (use AAAA-MM-DD)") from erro
