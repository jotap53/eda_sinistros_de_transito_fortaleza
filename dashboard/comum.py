"""Peças compartilhadas pelas páginas: dados, cores, formatação e layout."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DADOS = Path(__file__).parent / "dados"

FAIXAS = ["Madrugada", "Manhã", "Tarde", "Noite"]
FAIXAS_ROTULO = {"Madrugada": "Madrugada<br>0h-6h", "Manhã": "Manhã<br>6h-12h",
                 "Tarde": "Tarde<br>12h-18h", "Noite": "Noite<br>18h-24h"}
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
VEICULOS = {"v_automovel": "Automóvel", "v_moto": "Moto", "v_onibus": "Ônibus",
            "v_caminhao": "Caminhão", "v_bicicleta": "Bicicleta"}
ANOS = 10  # 2015 a 2024


# ------------------------------------------------------------------ Dados

@st.cache_data
def base():
    return pd.read_parquet(DADOS / "sinistros.parquet")


@st.cache_data
def tabela(nome):
    return pd.read_parquet(DADOS / f"{nome}.parquet")


@st.cache_data
def resultados():
    with open(DADOS / "resultados.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def geojson_bairros():
    with open(DADOS / "bairros.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def populacao_bairros():
    g = geojson_bairros()
    return pd.Series({f["properties"]["bairro"]: f["properties"]["populacao"]
                      for f in g["features"]})


# ------------------------------------------------------------------ Cores

def celular():
    """Detecta celular pelo navegador (para ajustar o zoom do mapa)."""
    agente = st.context.headers.get("User-Agent", "")
    return any(x in agente for x in ("Mobile", "Android", "iPhone"))


def escuro():
    return st.context.theme.type == "dark"


def cores():
    if escuro():
        return {"azul": "#3987e5", "laranja": "#d95926", "verde": "#199e70",
                "cinza": "#5a5955", "texto2": "#c3c2b7", "grade": "#2c2c2a",
                "rampa": ["#1c2f4a", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb"]}
    return {"azul": "#2a78d6", "laranja": "#eb6834", "verde": "#1baf7a",
            "cinza": "#c3c2b7", "texto2": "#52514e", "grade": "#e1e0d9",
            "rampa": ["#eef4fc", "#b7d3f6", "#6da7ec", "#256abf", "#0d366b"]}


# ------------------------------------------------------------------ Formatação

def fmt(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=1):
    return fmt(v, casas) + "%"


def wilson(eventos, n, z=1.96):
    """Intervalo de confiança de Wilson para uma proporção (em %)."""
    eventos, n = np.asarray(eventos, float), np.asarray(n, float)
    p = eventos / n
    centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    meia = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return 100 * (centro - meia), 100 * (centro + meia)


# ------------------------------------------------------------------ Layout

CSS = """
<style>
/* Menos espaço em volta do conteúdo */
.block-container {padding-top: 3.6rem; padding-bottom: 0.4rem; max-width: 100%;}
[data-testid="stMainBlockContainer"] {padding-left: 1.4rem; padding-right: 1.4rem;}
div[data-testid="stVerticalBlock"] {gap: 0.55rem;}
h1, h2, h3 {padding-top: 0 !important; padding-bottom: 0 !important;}
[data-testid="stMetric"] {padding: 0.45rem 0.8rem;}
[data-testid="stMetricValue"] {font-size: 1.55rem;}

/* Áreas de gráfico: a altura de cada uma é definida em area(), conforme a página */
[class*="st-key-g1-"], [class*="st-key-g2-"], [class*="st-key-mapa"] {
    overflow: hidden !important; display: flex; flex-direction: column;}
[class*="st-key-g1-"] > div, [class*="st-key-g2-"] > div, [class*="st-key-mapa"] > div {
    flex: 1 1 auto; min-height: 0; height: 100% !important;}
[class*="st-key-g1-"] [data-testid="stPlotlyChart"], [class*="st-key-g2-"] [data-testid="stPlotlyChart"],
[class*="st-key-mapa"] [data-testid="stDeckGlJsonChart"] {height: 100% !important;}

/* Rodapé fixo com o aviso e a fonte */
.rodape {position: fixed; left: 0; right: 0; bottom: 0; z-index: 100; padding: 4px 1.4rem;
    font-size: 0.72rem; line-height: 1.3; opacity: 0.85; text-align: center;
    background: var(--st-background-color, inherit); border-top: 1px solid rgba(128,128,128,0.18);}
.block-container {padding-bottom: 30px !important;}

/* Celular: os gráficos empilham; cada um ocupa no máximo uma tela */
@media (max-width: 640px) {
    .block-container {padding-top: 3.2rem;}
    [data-testid="stMainBlockContainer"] {padding-left: 0.7rem; padding-right: 0.7rem;}
    [data-testid="stMetricValue"] {font-size: 1.25rem;}
    .rodape {font-size: 0.66rem; padding: 3px 0.7rem;}
    /* Cartões de resumo em 2 x 2 */
    .st-key-kpis [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important; gap: 0.5rem;}
    .st-key-kpis [data-testid="stColumn"] {flex: 1 1 calc(50% - 0.5rem) !important;
        min-width: calc(50% - 0.5rem) !important;}
}
</style>
"""


def estilo():
    st.html(CSS)
    st.html(f'<div class="rodape">Trabalho acadêmico (IFCE) · não é um site oficial da Prefeitura de '
            f'Fortaleza nem da AMC · Fonte: {FONTE}</div>')


FONTE = "dados abertos da Prefeitura de Fortaleza / AMC"
EQUIPE = ["Anady Carvalho", "João Pedro Martins", "Jordan Elias Barbosa", "Jordan Elizeu Barbosa",
          "Márcio Rosário"]


SOBRE = """
Este dashboard foi desenvolvido exclusivamente para *fins acadêmicos*, como parte do *trabalho da
primeira etapa da disciplina de Introdução à Ciência de Dados* (IFCE).

*Esta não é uma página oficial da Prefeitura de Fortaleza nem da AMC.* Os dados utilizados são
provenientes da base de **dados abertos disponibilizada pela Prefeitura de Fortaleza/AMC
(Autarquia Municipal de Trânsito e Cidadania)**, sendo empregados neste trabalho exclusivamente
para fins de análise e visualização de dados. Dados de população: IBGE, Censo 2022. Malha viária:
OpenStreetMap.

*Equipe:*
"""


def sobre():
    st.markdown(SOBRE + "\n".join(f"- {nome}" for nome in EQUIPE)
                + "\n\n*Professor:* Valberto Feitosa")


def titulo(texto, ajuda=None):
    """Título da página com o botão 'Sobre este projeto' à direita."""
    with st.container(horizontal=True, horizontal_alignment="distribute",
                      vertical_alignment="center", key="linha-titulo"):
        st.markdown(f"#### {texto}", help=ajuda, width="content")
        with st.popover("Sobre", icon=":material/info:", help="Sobre este projeto"):
            sobre()


def subtitulo(texto, ajuda=None):
    st.markdown(f"**{texto}**", help=ajuda)


def area(chave, reserva, celular="58dvh"):
    """Container de gráfico que ocupa a altura da tela menos `reserva` px.

    `reserva` é o espaço acima (navegação, título, controles) e abaixo (rodapé) da
    área, medido para cada página. No celular, a altura é fixa em `celular`.
    """
    st.html(f"""<style>
    .st-key-{chave} {{flex: 0 0 calc(100dvh - {reserva}px) !important;
        height: calc(100dvh - {reserva}px) !important; min-height: 240px;}}
    @media (max-width: 640px) {{
        .st-key-{chave} {{flex-basis: {celular} !important; height: {celular} !important;}}}}
    </style>""")
    return st.container(key=chave, border=False)


def layout(fig, legenda=False, margem=None):
    m = dict(l=8, r=8, t=8, b=8)
    if margem:
        m.update(margem)
    fig.update_layout(
        margin=m, separators=",.", showlegend=legenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    title_text=""),
        hoverlabel=dict(namelength=-1), bargap=0.25,
    )
    return fig


def grafico(fig, chave=None):
    """Mostra a figura. Use uma `chave` diferente quando o tipo de gráfico muda no mesmo lugar,
    para o Plotly não reaproveitar o estado (eixos) do gráfico anterior."""
    st.plotly_chart(fig, height="stretch", theme="streamlit", key=chave,
                    config={"displayModeBar": False, "responsive": True})


def texto_dentro(fig):
    """Valores dentro da base das barras, em branco (quando há linha ou intervalo na ponta)."""
    fig.update_traces(textposition="inside", insidetextanchor="start",
                      textfont=dict(color="white"), selector=dict(type="bar"))
    return fig


def barras_h(rotulos, valores, cor, texto, hover=None, destaque=None, cor_destaque=None):
    """Barras horizontais com o valor escrito na ponta (maior em cima)."""
    cores_barras = [cor_destaque if (destaque and r in destaque) else cor for r in rotulos]
    fig = go.Figure(go.Bar(
        x=valores, y=rotulos, orientation="h", marker_color=cores_barras,
        text=texto, textposition="outside", cliponaxis=False,
        hovertemplate=hover or "%{y}: %{x}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix="  ")
    fig.update_xaxes(visible=False, range=[0, max(valores) * 1.22])
    return layout(fig)


# ------------------------------------------------------------------ Filtros do mapa

def filtrar(df, anos, dias, faixas, severidade, veiculos, naturezas, bairros):
    m = df["ano"].between(*anos)
    if dias == "Dias úteis":
        m &= ~df["fim_de_semana"]
    elif dias == "Fim de semana":
        m &= df["fim_de_semana"]
    if faixas:
        m &= df["faixa_horaria"].isin(faixas)
    if severidade == "Com vítima":
        m &= df["vitimas"] > 0
    elif severidade == "Fatais":
        m &= df["fatal"]
    if veiculos:
        col = [k for k, v in VEICULOS.items() if v in veiculos]
        m &= df[col].any(axis=1)
    if naturezas:
        m &= df["natureza"].isin(naturezas)
    if bairros:
        m &= df["bairro"].isin(bairros)
    return df[m]
