import matplotlib.pyplot as plt

SUPERFICIE = "#fcfcfb"
TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_MUTED = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"

AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERMELHO = "#e34948"


def aplicar_estilo(eixo: plt.Axes) -> None:
    """Aplica o estilo padrão (fundo, grade discreta, eixos sem moldura)."""
    eixo.set_facecolor(SUPERFICIE)
    eixo.figure.set_facecolor(SUPERFICIE)
    eixo.grid(axis="y", color=GRADE, linewidth=0.8, zorder=0)
    eixo.set_axisbelow(True)
    for lado in ("top", "right"):
        eixo.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eixo.spines[lado].set_color(EIXO)
    eixo.tick_params(colors=TINTA_SECUNDARIA)
    eixo.title.set_color(TINTA_PRIMARIA)
    eixo.xaxis.label.set_color(TINTA_SECUNDARIA)
    eixo.yaxis.label.set_color(TINTA_SECUNDARIA)
