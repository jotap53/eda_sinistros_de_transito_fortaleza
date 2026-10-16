"""Gráficos do projeto.

Estilo único para todas as figuras: fundo claro, grade em linha fina só no
eixo de valor, uma cor quando há uma série (azul), destaque em laranja com o
restante em cinza, rampa azul para magnitudes e azul<->vermelho com meio
cinza para valores com sinal. Os títulos afirmam o achado; o subtítulo diz o
que está sendo medido; o rodapé dá a fonte.

Cada função recebe o resultado da análise correspondente (analises.py),
salva a figura em figuras/ e a devolve.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch

from . import config

# ---------------------------------------------------------------- Paleta

FUNDO = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
CINZA = "#c3c2b7"
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE_AGUA = "#1baf7a"
AMARELO = "#eda100"
MAGENTA = "#e87ba4"
VIOLETA = "#6250d6"
CATEGORICAS = [AZUL, LARANJA, VERDE_AGUA, AMARELO, MAGENTA, "#008300", VIOLETA]

RAMPA_AZUL = LinearSegmentedColormap.from_list(
    "azul", ["#f3f7fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
             "#184f95", "#0d366b"])
DIVERGENTE = LinearSegmentedColormap.from_list(
    "divergente", ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f2a3a2", "#e34948",
                   "#a32828"])

FONTE_PADRAO = "Fonte: AMC / Prefeitura de Fortaleza, sinistros de trânsito 2015-2024. Elaboração própria."


def aplicar_estilo():
    mpl.rcParams.update({
        "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
        "text.color": TINTA, "axes.labelcolor": TINTA_2,
        "xtick.color": TINTA_3, "ytick.color": TINTA_3,
        "xtick.labelcolor": TINTA_2, "ytick.labelcolor": TINTA_2,
        "axes.edgecolor": EIXO, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "grid.color": GRADE, "grid.linewidth": 0.6,
        "grid.linestyle": "-", "axes.axisbelow": True,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "legend.fontsize": 9,
        "axes.titlelocation": "left",
    })


aplicar_estilo()


def _fmt(n, casas=0):
    """Número no padrão brasileiro (1.234,5)."""
    s = f"{n:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(n, casas=1):
    return f"{_fmt(n, casas)}%"


def _cabecalho(fig, titulo, subtitulo=None, fonte=FONTE_PADRAO, topo=0.97):
    fig.text(0.02, topo, titulo, fontsize=14, fontweight="bold", color=TINTA,
             ha="left", va="top")
    if subtitulo:
        fig.text(0.02, topo - 0.055, subtitulo, fontsize=10, color=TINTA_2,
                 ha="left", va="top")
    if fonte:
        fig.text(0.02, 0.012, fonte, fontsize=7.5, color=TINTA_3, ha="left", va="bottom")


def _afastar(valores, minimo):
    """Ajusta posições (ex.: y de rótulos) para ficarem a pelo menos `minimo` entre si."""
    ordem = np.argsort(valores)
    saida = np.array(valores, dtype=float)
    for i in range(1, len(ordem)):
        anterior, atual = ordem[i - 1], ordem[i]
        if saida[atual] - saida[anterior] < minimo:
            saida[atual] = saida[anterior] + minimo
    return saida


def _pct_eixo(ax, eixo="x", casas=1):
    fmt = mpl.ticker.FuncFormatter(lambda v, _: f"{_fmt(v, casas)}%")
    (ax.xaxis if eixo == "x" else ax.yaxis).set_major_formatter(fmt)


def _eixo_log(ax, marcas=(0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5)):
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(mpl.ticker.FixedLocator(marcas))
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: _fmt(v, 2).rstrip("0").rstrip(",")))
    ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())


def _grade(ax, eixo="y"):
    ax.grid(True, axis=eixo)
    if eixo == "x":
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
    else:
        ax.spines["left"].set_visible(False)


def salvar(fig, nome, pasta=None):
    pasta = pasta or config.FIGURAS
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.png"
    fig.savefig(caminho, dpi=200)
    return caminho


def _figura(largura=11, altura=6, topo=0.83, base=0.1, esquerda=0.08, direita=0.97, **kw):
    fig, ax = plt.subplots(figsize=(largura, altura), **kw)
    fig.subplots_adjust(top=topo, bottom=base, left=esquerda, right=direita)
    return fig, ax


def _barras_h(ax, valores, cores=AZUL, rotulos=None, fmt=lambda v: _fmt(v)):
    """Barras horizontais finas, com o valor escrito na ponta."""
    y = np.arange(len(valores))[::-1]
    ax.barh(y, valores.values, color=cores, height=0.62)
    ax.set_yticks(y, rotulos if rotulos is not None else valores.index)
    folga = valores.max() * 0.01
    for yi, v in zip(y, valores.values):
        ax.text(v + folga, yi, fmt(v), va="center", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, valores.max() * 1.15)
    _grade(ax, "x")
    ax.tick_params(axis="y", length=0)


def _pontos_ic(ax, tab, cor=AZUL, destaque=None, rotulo_n=True):
    """Gráfico de pontos com intervalo de confiança (tabela com pct, ic_inf, ic_sup, n)."""
    y = np.arange(len(tab))[::-1]
    cores = [LARANJA if (destaque and i in destaque) else cor for i in tab.index]
    ax.hlines(y, tab["ic_inf"], tab["ic_sup"], color=cores, linewidth=2, alpha=0.55)
    ax.scatter(tab["pct"], y, color=cores, s=55, zorder=3, edgecolor=FUNDO, linewidth=1.5)
    rotulos = [f"{i}  (n={_fmt(n)})" if rotulo_n else str(i)
               for i, n in zip(tab.index, tab["n"])]
    ax.set_yticks(y, rotulos)
    for yi, (_, r) in zip(y, tab.iterrows()):
        ax.text(r["ic_sup"], yi + 0.18, f" {_pct(r['pct'], 2)}", va="bottom", fontsize=8.5,
                color=TINTA_2)
    _grade(ax, "x")
    ax.set_xlim(left=0)
    _pct_eixo(ax, "x", 1)


# ---------------------------------------------------------------- 00 Pipeline

def fig00_pipeline():
    etapas = [
        ("1. Ingestão", "Leitura da base sinistro_transito_final.csv (130.820 registros) e dos dados\n"
         "externos: malha e população dos bairros (IBGE, Censo 2022) e malha viária (OpenStreetMap).",
         "notebook 01"),
        ("2. Transformação e enriquecimento", "Remoção de duplicatas, severidade recalculada pelas vítimas, bairro oficial\n"
         "pelas coordenadas, nomes de vias unificados, 'não informado' explícito.",
         "notebook 01"),
        ("3. Modelo analítico e visualização", "Passos 1 a 8 da análise exploratória: tempo, horários, bairros (com taxas\n"
         "por habitante), veículos, letalidade com intervalo de confiança e correlação.",
         "notebook 02 e 04"),
        ("4. Validação de hipóteses", "Passos 9 a 11: qui-quadrado sem 'não informado', Kruskal-Wallis e as 5\n"
         "hipóteses com regressões (logística, Poisson, Binomial Negativa) e quebra estrutural.",
         "notebook 03"),
    ]
    fig = plt.figure(figsize=(11, 8.6))
    _cabecalho(fig, "Pipeline de dados: sinistros de trânsito em Fortaleza",
               "As quatro etapas do projeto, na ordem em que são executadas", fonte=None)
    altura, gap, topo = 0.155, 0.045, 0.85
    for i, (nome, desc, onde) in enumerate(etapas):
        y = topo - i * (altura + gap) - altura
        caixa = FancyBboxPatch((0.06, y), 0.88, altura, boxstyle="round,pad=0,rounding_size=0.015",
                               transform=fig.transFigure, facecolor="#f0f5fc",
                               edgecolor=AZUL, linewidth=1.2)
        fig.add_artist(caixa)
        fig.text(0.09, y + altura - 0.03, nome, fontsize=12.5, fontweight="bold", va="top")
        fig.text(0.91, y + altura - 0.03, onde, fontsize=9, color=AZUL, va="top", ha="right")
        fig.text(0.09, y + altura - 0.075, desc, fontsize=9.5, color=TINTA_2, va="top",
                 linespacing=1.5)
        if i < len(etapas) - 1:
            fig.add_artist(mpl.patches.FancyArrowPatch(
                (0.5, y - 0.004), (0.5, y - gap + 0.004), transform=fig.transFigure,
                arrowstyle="-|>", mutation_scale=16, color=TINTA_3, linewidth=1.4))
    fig.text(0.06, 0.03, "Classe TrafegoPipeline (src/sinistros/pipeline.py) executa as quatro etapas "
             "de ponta a ponta: notebooks/00_pipeline.ipynb.", fontsize=8.5, color=TINTA_3)
    salvar(fig, "00_pipeline")
    return fig


# ---------------------------------------------------------------- 01 Qualidade

def fig01_qualidade(res):
    tab = res["tabela"]
    fig, ax = _figura(11, 6, esquerda=0.07, direita=0.74)
    posicoes = _afastar(tab.iloc[-1].to_numpy(), 4.5)
    for cor, col, y in zip(CATEGORICAS, tab.columns, posicoes):
        ax.plot(tab.index, tab[col], color=cor, linewidth=2, marker="o", markersize=5)
        ax.text(tab.index[-1] + 0.25, y, f"{col}  {_pct(tab[col].iloc[-1], 0)}",
                color=TINTA_2, fontsize=8.5, va="center")
    ax.set_ylim(0, 100)
    ax.set_xticks(tab.index)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    _grade(ax, "y")
    ax.set_ylabel("% dos acidentes do ano sem a informação")
    _cabecalho(fig, "O preenchimento piorou: 'controle de tráfego' falta em 8 de cada 10 registros desde 2021",
               "Percentual de acidentes com a variável como 'não informado', por ano")
    salvar(fig, "01_qualidade_nao_informado_por_ano")
    return fig


# ---------------------------------------------------------------- Passo 1

def fig02_evolucao_anual(res):
    a = res["anual"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.6))
    fig.subplots_adjust(top=0.8, bottom=0.12, left=0.06, right=0.98, wspace=0.22)
    cores = [CINZA if ano >= config.ANO_QUEBRA else AZUL for ano in a.index]
    ax1.bar(a.index, a["acidentes"], color=cores, width=0.65)
    for x, v in zip(a.index, a["acidentes"]):
        ax1.text(x, v + 200, _fmt(v / 1000, 1) + " mil", ha="center", fontsize=8, color=TINTA_2)
    ax1.set_title("Acidentes registrados por ano", fontsize=10.5, color=TINTA, pad=10)
    ax1.annotate("mudança de patamar\nem jan/2018", xy=(2017.6, 15000), xytext=(2019.3, 17500),
                 fontsize=8.5, color=TINTA_2,
                 arrowprops=dict(arrowstyle="-", color=TINTA_3, linewidth=0.8))
    ax2.bar(a.index, a["mortos"], color=LARANJA, width=0.65)
    for x, v in zip(a.index, a["mortos"]):
        ax2.text(x, v + 3, _fmt(v), ha="center", fontsize=8, color=TINTA_2)
    ax2.set_title("Mortos por ano", fontsize=10.5, color=TINTA, pad=10)
    for ax in (ax1, ax2):
        ax.set_xticks(a.index, [str(x) for x in a.index], rotation=0, fontsize=8.5)
        _grade(ax, "y")
        ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: _fmt(v)))
    _cabecalho(fig, "Os acidentes caíram de patamar em 2018; as mortes caem aos poucos, ano a ano",
               f"Mortes: de {_fmt(a['mortos'].iloc[0])} em 2015 para {_fmt(a['mortos'].iloc[-1])} em 2024. "
               "Acidentes: média de 17,4 mil/ano até 2017 e 11,2 mil/ano depois.")
    salvar(fig, "02_acidentes_e_mortes_por_ano")
    return fig


def fig03_severidade(res):
    s = res["severidade"]
    ordem = ["Ferido", "Ileso", "Fatal", "Sem informação"]
    s = s.reindex([o for o in ordem if o in s.index])
    fig, ax = _figura(10, 4.6, topo=0.78, esquerda=0.15)
    cores = [AZUL, AZUL, LARANJA, CINZA]
    _barras_h(ax, s["acidentes"], cores=cores,
              fmt=lambda v: f"{_fmt(v)}  ({_pct(100 * v / s['acidentes'].sum())})")
    ax.set_xticks([])
    _cabecalho(fig, "8 em cada 10 acidentes registrados deixam feridos; 1,5% são fatais",
               "Severidade recalculada pelas contagens de vítimas (fatal: houve morto; ferido: houve ferido)")
    salvar(fig, "03_severidade")
    return fig


# ---------------------------------------------------------------- Passos 2 e 3

def fig04_por_hora(res):
    h = res["por_hora"]
    fig, ax = _figura(11, 5.4)
    cores = [LARANJA if i in (7, 16) else AZUL for i in h.index]
    ax.bar(h.index, h.values, color=cores, width=0.7)
    for i in (7, 16):
        ax.text(i, h[i] + 120, _fmt(h[i]), ha="center", fontsize=9, color=TINTA, fontweight="bold")
    ax.set_xticks(range(24), [f"{i}h" for i in range(24)], fontsize=8.5)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: _fmt(v)))
    _grade(ax, "y")
    ax.set_ylabel("Acidentes (2015-2024)")
    _cabecalho(fig, "Os acidentes acompanham o pico de deslocamentos: 7h e 16h",
               "Total de acidentes por hora do dia, 2015-2024")
    salvar(fig, "04_acidentes_por_hora")
    return fig


def fig05_dia_hora(res):
    m = res["media_dia_hora"]
    fig, ax = _figura(12, 5.2, esquerda=0.08, direita=0.93)
    im = ax.imshow(m.values, aspect="auto", cmap=RAMPA_AZUL)
    ax.set_xticks(range(24), [f"{i}h" for i in range(24)], fontsize=8.5)
    ax.set_yticks(range(len(m.index)), m.index)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.outline.set_visible(False)
    cb.set_label("Acidentes por dia, em média", color=TINTA_2)
    _cabecalho(fig, "Nos dias úteis, picos às 7h e às 16-17h; no fim de semana, as madrugadas se destacam",
               "Média de acidentes por dia em cada hora, por dia da semana (2015-2024)")
    salvar(fig, "05_mapa_calor_dia_hora")
    return fig


def fig06_letalidade_faixa_fds(res):
    t = res["letalidade_fds_faixa"].reset_index()
    fig, ax = _figura(11, 5.6, esquerda=0.1, base=0.16)
    x = np.arange(len(config.FAIXAS))
    for desloc, (fds, cor, nome) in zip((-0.12, 0.12), [(False, AZUL, "Dia útil"),
                                                        (True, LARANJA, "Fim de semana")]):
        d = t[t["fim_de_semana"] == fds].set_index("faixa_horaria").reindex(config.FAIXAS)
        ax.vlines(x + desloc, d["ic_inf"], d["ic_sup"], color=cor, linewidth=2, alpha=0.55)
        ax.scatter(x + desloc, d["pct"], color=cor, s=60, zorder=3, label=nome,
                   edgecolor=FUNDO, linewidth=1.5)
        for xi, v in zip(x + desloc, d["pct"]):
            ax.text(xi + 0.04, v, _pct(v, 2), fontsize=8.5, color=TINTA_2, va="center")
    ax.set_xticks(x, ["Madrugada\n0h-6h", "Manhã\n6h-12h", "Tarde\n12h-18h", "Noite\n18h-24h"])
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{_fmt(v, 1)}%"))
    _grade(ax, "y")
    ax.set_ylabel("% de acidentes fatais (letalidade)")
    ax.legend(loc="upper right")
    _cabecalho(fig, "A madrugada do fim de semana tem a maior letalidade: 3 vezes a da manhã de dia útil",
               "% dos acidentes com morte, por faixa horária e tipo de dia, com intervalo de confiança de 95%")
    salvar(fig, "06_letalidade_faixa_fim_de_semana")
    return fig


# ---------------------------------------------------------------- Passo 4

def fig07_bairros(res):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6.6))
    fig.subplots_adjust(top=0.8, bottom=0.08, left=0.14, right=0.97, wspace=0.62)
    ta = res["top_acidentes"]["acidentes"].head(12)
    tt = res["top_taxa"]["acidentes_10k_hab_ano"].head(12)
    comuns = set(ta.index) & set(tt.index)
    _barras_h(ax1, ta, cores=[LARANJA if i in comuns else AZUL for i in ta.index])
    _barras_h(ax2, tt, cores=[LARANJA if i in comuns else AZUL for i in tt.index],
              fmt=lambda v: _fmt(v, 0))
    ax1.set_title("Total de acidentes (2015-2024)", fontsize=10.5, pad=8)
    ax2.set_title("Acidentes por 10 mil habitantes, por ano", fontsize=10.5, pad=8)
    for ax in (ax1, ax2):
        ax.set_xticks([])
    _cabecalho(fig, "O Centro lidera nas duas medidas; considerando a população, entram bairros de passagem",
               "Laranja: bairros que estão nos dois rankings. População: IBGE, Censo 2022.",
               fonte=FONTE_PADRAO + " População: IBGE, Censo 2022.")
    salvar(fig, "07_bairros_total_e_taxa")
    return fig


def _mapa_bairros(b, coluna, titulo, subtitulo, rotulo_cor, nome, destacar=8, fonte_extra=""):
    fig, ax = plt.subplots(figsize=(10, 8.2))
    fig.subplots_adjust(top=0.87, bottom=0.04, left=0.02, right=0.98)
    g = b.to_crs(31984)
    g.plot(column=coluna, cmap=RAMPA_AZUL, ax=ax, edgecolor=FUNDO, linewidth=0.5,
           legend=True, legend_kwds={"shrink": 0.55, "label": rotulo_cor, "pad": 0.01})
    # Rótulos dos maiores valores, afastados verticalmente quando ficam próximos
    top = g.nlargest(destacar, coluna)
    pontos = [r.geometry.representative_point() for _, r in top.iterrows()]
    xs = np.array([p.x for p in pontos])
    ys = np.array([p.y for p in pontos])
    # Rótulo que colide com um anterior vai para fora do mapa, à esquerda
    xs_rotulo = xs.copy()
    for i in range(len(ys)):
        for j in range(i):
            if abs(xs_rotulo[i] - xs_rotulo[j]) < 3000 and abs(ys[i] - ys[j]) < 900:
                xs_rotulo[i] = xs[i] - 5500
    for nome_bairro, x, xr, y in zip(top["bairro"], xs, xs_rotulo, ys):
        ax.annotate(nome_bairro, (x, y), xytext=(xr, y), fontsize=7.5, color=TINTA,
                    ha="center", va="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc=FUNDO, ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="-", color=TINTA_3, linewidth=0.6)
                    if xr != x else None)
    ax.set_axis_off()
    cb = fig.axes[-1]
    cb.yaxis.label.set_color(TINTA_2)
    _cabecalho(fig, titulo, subtitulo, fonte=FONTE_PADRAO + fonte_extra)
    salvar(fig, nome)
    return fig


def fig08_mapa_taxa_acidentes(res):
    return _mapa_bairros(
        res["bairros"], "acidentes_10k_hab_ano",
        "Acidentes por habitante: Centro e bairros de comércio e passagem lideram",
        "Acidentes por 10 mil habitantes, por ano (2015-2024). Rótulos: os 8 maiores.",
        "Acidentes / 10 mil hab. / ano", "08_mapa_bairros_acidentes_por_habitante",
        fonte_extra=" Malha e população: IBGE, Censo 2022.")


def fig09_mapa_mortes(res):
    return _mapa_bairros(
        res["bairros"], "mortos_100k_hab_ano",
        "Mortes por habitante: além do Centro, pesam bairros cortados por rodovias, como Cajazeiras (BR-116)",
        "Mortos por 100 mil habitantes, por ano (2015-2024). Bairros pequenos variam muito ao acaso.",
        "Mortos / 100 mil hab. / ano", "09_mapa_bairros_mortes_por_habitante",
        fonte_extra=" Malha e população: IBGE, Censo 2022.")


def fig10_bairros_mortes_ic(res):
    t = res["top_taxa_mortos"].head(12)
    tab = pd.DataFrame({"pct": t["mortos_100k_hab_ano"], "ic_inf": t["mortos_100k_ic_inf"],
                        "ic_sup": t["mortos_100k_ic_sup"], "n": t["mortos"]})
    media = res["resumo"]["media_cidade_mortos_100k_hab_ano"]
    fig, ax = _figura(11, 6, esquerda=0.22)
    y = np.arange(len(tab))[::-1]
    ax.hlines(y, tab["ic_inf"], tab["ic_sup"], color=AZUL, linewidth=2, alpha=0.5)
    ax.scatter(tab["pct"], y, color=AZUL, s=55, zorder=3, edgecolor=FUNDO, linewidth=1.5)
    ax.set_yticks(y, [f"{i}  ({_fmt(n)} mortes)" for i, n in zip(tab.index, tab["n"])])
    for yi, (_, r) in zip(y, tab.iterrows()):
        ax.text(r["ic_sup"] + 0.8, yi, _fmt(r["pct"], 1), va="center", fontsize=8.5, color=TINTA_2)
    ax.axvline(media, color=LARANJA, linewidth=1.2)
    ax.text(media + 0.6, len(tab) - 0.4, f"média da cidade: {_fmt(media, 1)}", color=LARANJA,
            fontsize=8.5, va="bottom")
    _grade(ax, "x")
    ax.set_xlim(0, None)
    ax.set_xlabel("Mortos por 100 mil habitantes, por ano (IC 95%)")
    _cabecalho(fig, "Bairros com mais mortes por habitante: os intervalos são largos, mas ficam acima da média",
               "Só bairros com 10 mortes ou mais no período; IC de Poisson exato",
               fonte=FONTE_PADRAO + " População: IBGE, Censo 2022.")
    salvar(fig, "10_bairros_mortes_por_habitante_ic")
    return fig


# ---------------------------------------------------------------- Passos 5 e 6

def fig11_veiculos(res):
    p = res["presenca"].head(7)
    fig, ax = _figura(10, 4.8, topo=0.8, esquerda=0.15)
    rot = [config.NOMES_VEICULOS[i] for i in p.index]
    _barras_h(ax, p["pct_acidentes"], rotulos=rot,
              fmt=lambda v: _pct(v))
    ax.set_xticks([])
    _cabecalho(fig, "Automóvel está em 70% dos acidentes e a moto em 63%",
               f"% dos acidentes em que cada tipo de veículo esteve envolvido "
               f"(só os {_fmt(res['resumo']['acidentes_com_veiculo_informado'])} com veículos informados)")
    salvar(fig, "11_veiculos_envolvidos")
    return fig


def fig12_coocorrencia(res):
    m = res["matriz"]
    fig, ax = _figura(9.6, 7.6, topo=0.84, base=0.08, esquerda=0.16, direita=0.97)
    im = ax.imshow(np.log10(m.values.astype(float) + 1), cmap=RAMPA_AZUL)
    for i in range(len(m)):
        for j in range(len(m)):
            v = m.values[i, j]
            claro = np.log10(v + 1) > 3.3
            ax.text(j, i, _fmt(v), ha="center", va="center", fontsize=9.5,
                    color="white" if claro else TINTA,
                    fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(len(m)), m.columns)
    ax.set_yticks(range(len(m)), m.index)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    _cabecalho(fig, "Carro + moto é a combinação mais comum: 44,9 mil acidentes",
               "Fora da diagonal: acidentes com os dois tipos. Na diagonal (negrito): acidentes só com aquele tipo.")
    salvar(fig, "12_coocorrencia_veiculos")
    return fig


# ---------------------------------------------------------------- Passo 7

def fig13_letalidade_veiculo(res):
    t = res["por_veiculo"]
    t = t[t["n"] >= 100]
    fig, ax = _figura(11, 5.6, esquerda=0.22)
    _pontos_ic(ax, t, destaque=t.index[t["amostra_pequena"]].tolist())
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{_fmt(v, 0)}%"))
    ax.set_xlabel("% dos acidentes com o veículo envolvido que foram fatais (IC 95%)")
    _cabecalho(fig, "Com ônibus, caminhão ou bicicleta, o acidente é cerca de 3 a 4 vezes mais letal que com automóvel",
               "Laranja: menos de 1.000 acidentes, estimativa imprecisa. Trem e tração animal "
               "(menos de 100 casos) ficam de fora.")
    salvar(fig, "13_letalidade_por_veiculo")
    return fig


def fig14_letalidade_natureza(res):
    t = res["por_natureza"]
    fig, ax = _figura(11, 5.8, esquerda=0.24)
    _pontos_ic(ax, t, destaque=["Atropelamento", "Choque c/ obstáculo fixo"])
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{_fmt(v, 0)}%"))
    ax.set_xlabel("% de acidentes fatais (IC 95%)")
    _cabecalho(fig, "Atropelamentos e choques com obstáculo são os acidentes mais letais",
               "Letalidade por natureza do acidente (só naturezas com 500 casos ou mais)")
    salvar(fig, "14_letalidade_por_natureza")
    return fig


# ---------------------------------------------------------------- Passo 8

def fig15_correlacao(res):
    # Triângulo inferior sem a diagonal: linhas da 2ª em diante, colunas até a penúltima
    c = res["matriz"].iloc[1:, :-1]
    fig, ax = _figura(10, 7.8, topo=0.86, base=0.15, esquerda=0.17, direita=0.95)
    mascara = np.triu(np.ones_like(c, dtype=bool), k=1)
    dados = np.ma.array(c.values, mask=mascara)
    im = ax.imshow(dados, cmap=DIVERGENTE, norm=TwoSlopeNorm(0, -1, 1))
    for i in range(len(c)):
        for j in range(i + 1):
            v = c.values[i, j]
            ax.text(j, i, _fmt(v, 2), ha="center", va="center", fontsize=8.5,
                    color="white" if abs(v) > 0.6 else TINTA)
    ax.set_xticks(range(c.shape[1]), c.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(c)), c.index)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: _fmt(v, 2)))
    _cabecalho(fig, "Moto se associa a feridos; automóvel, a ilesos",
               "Correlação de Spearman entre contagens por acidente (só acidentes com veículos informados)")
    salvar(fig, "15_correlacao_spearman")
    return fig


# ---------------------------------------------------------------- Passo 9

def _residuos(ax, r, titulo):
    res = r["residuos"]
    lim = max(abs(res.values.min()), abs(res.values.max()))
    im = ax.imshow(res.values, cmap=DIVERGENTE, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    for i in range(res.shape[0]):
        for j in range(res.shape[1]):
            v = res.values[i, j]
            ax.text(j, i, _fmt(v, 1), ha="center", va="center", fontsize=9,
                    color="white" if abs(v) > lim * 0.6 else TINTA)
    ax.set_xticks(range(res.shape[1]), res.columns)
    ax.set_yticks(range(res.shape[0]), res.index)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(titulo, fontsize=10, color=TINTA_2, pad=26)
    return im


def fig16_qui_quadrado(res):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
    fig.subplots_adjust(top=0.74, bottom=0.08, left=0.13, right=0.97, wspace=0.55)
    rc, rx = res["resumo"]["controle"], res["resumo"]["cruzamento"]
    _residuos(ax1, res["controle"],
              f"Controle de tráfego × severidade\nV de Cramér = {_fmt(rc['v_cramer'], 3)} "
              f"(era {_fmt(res['resumo']['controle_com_ni']['v_cramer'], 2)} com 'não informado')")
    _residuos(ax2, res["cruzamento"],
              f"Tipo de cruzamento × severidade\nV de Cramér = {_fmt(rx['v_cramer'], 3)}")
    _cabecalho(fig, "Sem os 'não informados', a associação com o controle de tráfego quase desaparece",
               "Resíduos padronizados do qui-quadrado: vermelho = mais casos que o esperado; azul = menos. "
               "|valor| > 2 é relevante.")
    salvar(fig, "16_qui_quadrado_residuos")
    return fig


# ---------------------------------------------------------------- Passo 10

def fig17_vitimas_natureza(res):
    m = res["medias_natureza"]
    fig, ax = _figura(10, 5.8, esquerda=0.24, topo=0.8)
    s = m["mean"]
    _barras_h(ax, s, cores=[LARANJA if v == s.max() else AZUL for v in s],
              fmt=lambda v: _fmt(v, 2))
    ax.set_xticks([])
    r = res["resumo"]["natureza"]
    _cabecalho(fig, "Atropelamentos deixam mais vítimas por acidente; colisões traseiras e engavetamentos, menos",
               f"Média de vítimas (feridos + mortos) por acidente. Kruskal-Wallis p < 0,001; "
               f"eta² = {_fmt(r['eta2'], 3)} (efeito moderado).")
    salvar(fig, "17_vitimas_por_natureza")
    return fig


# ---------------------------------------------------------------- Hipóteses

def _floresta(ax, tab, rotulo_x, referencia=1.0):
    y = np.arange(len(tab))[::-1]
    cores = [LARANJA if r.ic_inf > referencia else (AZUL if r.ic_sup < referencia else CINZA)
             for r in tab.itertuples()]
    ax.hlines(y, tab["ic_inf"], tab["ic_sup"], color=cores, linewidth=2.2)
    ax.scatter(tab["coef"], y, color=cores, s=60, zorder=3, edgecolor=FUNDO, linewidth=1.5)
    ax.axvline(referencia, color=TINTA_3, linewidth=1)
    ax.set_yticks(y, tab.index)
    for yi, r in zip(y, tab.itertuples()):
        ax.text(r.ic_sup * 1.03, yi, f"{_fmt(r.coef, 2)}  ({_fmt(r.ic_inf, 2)}-{_fmt(r.ic_sup, 2)})",
                va="center", fontsize=8.5, color=TINTA_2)
    _eixo_log(ax)
    _grade(ax, "x")
    ax.set_xlabel(rotulo_x)


def fig18_h1(res):
    t = res["odds_ratios"]
    fig, ax = _figura(11.5, 5.8, esquerda=0.3, direita=0.93)
    _floresta(ax, t, "Razão de chances de o acidente ser fatal (escala log, IC 95%)")
    ax.set_xlim(0.4, 5)
    _cabecalho(fig, "H1 confirmada: madrugada, noite e fim de semana elevam a chance de morte, "
               "cada um por si",
               "Regressão logística ajustada por faixa horária, tipo de dia, perfil de veículos e ano. "
               "Laranja: aumenta o risco; azul: reduz.")
    salvar(fig, "18_h1_razao_de_chances")
    return fig


def fig19_h2(res):
    p = res["pct_com_vitima"]
    p = p[p["n"] >= 1000]
    irr = res["irr"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6))
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.15, right=0.95, wspace=0.75)
    _barras_h(ax1, p["pct"], cores=[LARANJA if "oto" in str(i) else AZUL for i in p.index],
              fmt=lambda v: _pct(v, 0))
    ax1.set_xticks([])
    ax1.set_title("% dos acidentes com pelo menos uma vítima", fontsize=10.5, pad=8)
    _floresta(ax2, irr, "Razão de médias de vítimas vs. 'só automóvel' (IC 95%)")
    ax2.set_xlim(0.85, 2.4)
    ax2.set_title("Número de vítimas (Poisson, ajustado por ano)", fontsize=10.5, pad=8)
    _cabecalho(fig, "H2 confirmada: com moto envolvida, quase todo acidente tem vítima e o número "
               "de vítimas é 60% maior",
               "Só acidentes com veículos informados. Comparação com acidentes envolvendo só automóveis.")
    salvar(fig, "19_h2_motos_vitimas")
    return fig


def fig20_h3(res):
    s = res["serie"]
    a = res["mortes_anuais"]
    r = res["resumo"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.6), gridspec_kw={"width_ratios": [1.7, 1]})
    fig.subplots_adjust(top=0.78, bottom=0.12, left=0.06, right=0.98, wspace=0.18)
    ax1.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2020-12-31"), color=GRADE, alpha=0.8)
    ax1.text(pd.Timestamp("2020-03-15"), s["acidentes"].max() * 0.98, "pandemia", fontsize=8,
             color=TINTA_3, va="top")
    ax1.plot(s.index, s["acidentes"], color=CINZA, linewidth=1.2, label="Acidentes por mês")
    ax1.plot(s.index, s["ajuste_linear"], color=TINTA_3, linewidth=1.5, linestyle=(0, (4, 3)),
             label=f"Reta única (versão anterior), R² = {_fmt(r['r2_linear'], 2)}")
    ax1.plot(s.index, s["ajuste_segmentado"], color=AZUL, linewidth=2,
             label=f"Dois patamares + sazonalidade, R² = {_fmt(r['r2_segmentado'], 2)}")
    ax1.legend(loc="upper right", fontsize=8.5)
    ax1.set_title(f"Acidentes por mês: degrau de {_fmt(abs(r['degrau_mensal']))} acidentes/mês "
                  f"em {r['quebra_mes'][5:]}/{r['quebra_mes'][:4]}", fontsize=10.5, pad=8)
    _grade(ax1, "y")
    ax2.bar(a["ano"], a["mortos"], color=LARANJA, width=0.65, alpha=0.85)
    ax2.plot(a["ano"], a["ajuste"], color=TINTA, linewidth=1.8)
    ax2.set_xticks(a["ano"], [str(x)[2:] for x in a["ano"]])
    ax2.set_title(f"Mortos por ano: queda de {_fmt(abs(r['mortes_variacao_anual_pct']), 1)}% ao ano",
                  fontsize=10.5, pad=8)
    _grade(ax2, "y")
    _cabecalho(fig, "H3 revista: os acidentes mudaram de patamar em 2018; a queda contínua está nas mortes",
               "Esquerda: série mensal com modelo segmentado (erros HAC). "
               "Direita: mortos por ano com tendência de Poisson.")
    salvar(fig, "20_h3_tendencia")
    return fig


def fig21_h4(res):
    let = res["letalidade"]
    ors = res["odds_ratios"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    fig.subplots_adjust(top=0.76, bottom=0.14, left=0.15, right=0.95, wspace=0.6)
    _pontos_ic(ax1, let.sort_values("pct", ascending=False), destaque=["Sem controle"])
    ax1.set_xlabel("% de acidentes fatais (IC 95%)")
    ax1.set_title("Letalidade por controle de tráfego", fontsize=10.5, pad=8)
    _floresta(ax2, ors, "Razão de chances de morte (IC 95%)")
    ax2.set_title("Ajustado por faixa horária, dia e ano", fontsize=10.5, pad=8)
    ax2.set_xlim(0.6, 3)
    _cabecalho(fig, "H4 parcial: locais sem controle têm 60% mais chance de acidente fatal que semáforos",
               f"Só os {_fmt(res['resumo']['n_sem_ni'])} acidentes (39%) com controle informado. "
               f"V de Cramér da severidade: {_fmt(res['resumo']['v_cramer_sem_ni'], 2)} (fraco).")
    salvar(fig, "21_h4_controle_trafego")
    return fig


def fig22_h5(res):
    b = res["bairros"]
    r = res["resumo"]
    fig, ax = _figura(11, 7, topo=0.83, esquerda=0.09)
    ax.scatter(b["esperado"], b["acidentes"], s=np.sqrt(b["populacao"]) / 3, color=AZUL,
               alpha=0.55, edgecolor=FUNDO, linewidth=0.8)
    lim = [b[["esperado", "acidentes"]].min().min() * 0.8, b[["esperado", "acidentes"]].max().max() * 1.2]
    ax.plot(lim, lim, color=TINTA_3, linewidth=1)
    ax.text(lim[1] * 0.75, lim[1] * 0.62, "observado = esperado", color=TINTA_3, fontsize=8.5,
            rotation=33)
    destaque = pd.concat([b.nlargest(6, "razao_obs_esp"), b.nsmallest(3, "razao_obs_esp")])
    # Rótulos afastados na vertical (em escala log) para não se sobreporem
    y_rotulo = 10 ** _afastar(np.log10(destaque["acidentes"].to_numpy()), 0.055)
    for (_, x), yr in zip(destaque.iterrows(), y_rotulo):
        ax.scatter(x["esperado"], x["acidentes"], s=np.sqrt(x["populacao"]) / 3, color=LARANJA,
                   edgecolor=FUNDO, linewidth=0.8, zorder=3)
        ax.annotate(f"{x['bairro']} ({_fmt(x['razao_obs_esp'], 1)}×)",
                    (x["esperado"], x["acidentes"]), xytext=(x["esperado"] * 1.12, yr),
                    fontsize=8.5, color=TINTA, va="center",
                    arrowprops=dict(arrowstyle="-", color=TINTA_3, linewidth=0.5))
    ax.set_xscale("log")
    ax.set_yscale("log")
    for eixo in (ax.xaxis, ax.yaxis):
        eixo.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: _fmt(v)))
    _grade(ax, "both")
    ax.set_xlabel("Acidentes esperados pela população e pelos km de vias do bairro")
    ax.set_ylabel("Acidentes observados (2015-2024)")
    pr2 = r["pseudo_r2"]["População + km de vias"]
    _cabecalho(fig, "H5 revista: população e malha viária explicam cerca de 40% da variação entre bairros",
               f"Binomial Negativa com dados externos (pseudo-R² = {_fmt(pr2, 2)}; a versão anterior, "
               f"com R² = {_fmt(r['r2_circular_versao_anterior'], 2)}, era circular). Tamanho = população.",
               fonte=FONTE_PADRAO + " População: IBGE, Censo 2022. Vias: OpenStreetMap.")
    salvar(fig, "22_h5_bairros_observado_esperado")
    return fig


# ---------------------------------------------------------------- Vias

def fig23_vias(res):
    t = res["top"]
    fig, ax = _figura(11.5, 7.6, topo=0.85, esquerda=0.3, direita=0.96)
    y = np.arange(len(t))[::-1]
    ax.barh(y, t["acidentes"], color=AZUL, height=0.62)
    ax.set_yticks(y, t.index)
    for yi, (_, r) in zip(y, t.iterrows()):
        ax.text(r["acidentes"] + 25, yi, f"{_fmt(r['acidentes'])}   ·   {_fmt(r['mortos'])} mortos",
                va="center", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, t["acidentes"].max() * 1.3)
    ax.set_xticks([])
    _grade(ax, "x")
    def curto(nome):
        return nome.replace("Avenida ", "").replace("Av. ", "").replace("General ", "")
    nomes = [curto(n) for n in t.index[:3]]
    mais_mortes = curto(t["mortos"].idxmax())
    _cabecalho(fig, f"{nomes[0]}, {nomes[1]} e {nomes[2]} lideram; "
               f"a {mais_mortes} concentra mais mortes",
               f"As 20 vias com mais acidentes (2015-2024), depois de unificar as grafias dos nomes. "
               f"Elas somam {_pct(res['resumo']['pct_top'], 0)} dos acidentes.")
    salvar(fig, "23_vias_top20")
    return fig


def fig24_mapa_vias(df, res, bairros):
    """Mapa estático: pontos reais dos acidentes nas 10 vias mais críticas."""
    top = res["top"].head(8).index.tolist()
    g = bairros.to_crs(4326)
    fig, ax = plt.subplots(figsize=(10.5, 8.8))
    fig.subplots_adjust(top=0.88, bottom=0.03, left=0.02, right=0.98)
    g.plot(ax=ax, facecolor="#f0efec", edgecolor="#d9d8d2", linewidth=0.5)
    fundo = df.sample(min(len(df), 40000), random_state=0)
    ax.scatter(fundo["longitude"], fundo["latitude"], s=0.4, color=TINTA_3, alpha=0.25,
               linewidths=0)
    cores = CATEGORICAS + ["#e34948"]
    for cor, via in zip(cores, top):
        d = df[df["via"] == via]
        ax.scatter(d["longitude"], d["latitude"], s=3, color=cor, alpha=0.85, linewidths=0,
                   label=f"{via} ({_fmt(len(d))})")
    leg = ax.legend(loc="lower left", markerscale=5, fontsize=8.5, frameon=True,
                    facecolor=FUNDO, edgecolor="none")
    for h in leg.legend_handles:
        h.set_alpha(1)
    ax.set_aspect(1 / np.cos(np.deg2rad(-3.77)))
    ax.set_axis_off()
    _cabecalho(fig, "Onde ficam as 8 vias com mais acidentes",
               "Cada ponto é um acidente, na coordenada registrada. Cinza: amostra dos demais acidentes.",
               fonte=FONTE_PADRAO + " Limites dos bairros: IBGE.")
    salvar(fig, "24_mapa_vias_top8", pasta=config.MAPAS)
    return fig
