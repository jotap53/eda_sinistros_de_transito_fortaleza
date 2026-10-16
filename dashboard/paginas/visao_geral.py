import plotly.graph_objects as go
import streamlit as st

from comum import (area, base, cores, fmt, grafico, layout, pct, resultados, subtitulo, tabela,
                   texto_dentro, titulo)

df = base()
r = resultados()
c = cores()

titulo("Sinistros de trânsito em Fortaleza · 2015-2024",
       "Acidentes registrados pela AMC. Fontes: AMC / Prefeitura de Fortaleza, "
       "IBGE (Censo 2022) e OpenStreetMap.")

with st.container(key="kpis"):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Acidentes", fmt(len(df)), border=True,
              help="Acidentes registrados de 2015 a 2024, sem duplicatas.")
    k2.metric("Mortos", fmt(df["mortos"].sum()), border=True)
    k3.metric("Letalidade", pct(100 * df["fatal"].mean(), 2), border=True,
              help="% dos acidentes com ao menos uma morte.")
    k4.metric("Mortes por ano", pct(r["h3"]["mortes_variacao_anual_pct"], 1), border=True,
              help="Variação média anual das mortes de 2015 a 2024 (tendência de Poisson).")

anual = df.groupby("ano").agg(acidentes=("ano", "size"), mortos=("mortos", "sum"))
anos = anual.index.astype(str)

e, d = st.columns(2)
with e:
    t1, t2 = st.columns([1.3, 1], vertical_alignment="center")
    with t1:
        subtitulo("Acidentes",
                  "Em janeiro de 2018 o número de acidentes registrados cai de patamar, sem queda "
                  "gradual antes nem depois. A queda se concentra em acidentes sem vítima, o que "
                  "indica mudança no registro. 'Por dia': box plot do número de acidentes em "
                  "cada dia do ano (linha central = mediana; caixa = 1º a 3º quartil; pontos = "
                  "dias atípicos).")
    visao = t2.segmented_control("Visão", ["Por ano", "Por dia"], default="Por ano",
                                 required=True, label_visibility="collapsed", key="vis_acid")
    with area("g2-acidentes", 308):
        if visao == "Por ano":
            fig = go.Figure(go.Bar(
                x=anos, y=anual["acidentes"], marker_color=c["azul"],
                text=[fmt(v / 1000, 1) + " mil" for v in anual["acidentes"]],
                textposition="outside", cliponaxis=False,
                hovertemplate="%{x}: %{y:,.0f} acidentes<extra></extra>"))
            fig.update_yaxes(visible=False, range=[0, anual["acidentes"].max() * 1.15])
        else:
            por_dia = df.groupby("data").size().rename("acidentes").reset_index()
            por_dia["ano"] = por_dia["data"].dt.year.astype(str)
            fig = go.Figure(go.Box(
                x=por_dia["ano"].tolist(), y=por_dia["acidentes"].tolist(), marker_color=c["azul"],
                line_width=1.2, boxpoints="outliers", marker_size=3,
                hovertemplate="%{x}: %{y} acidentes no dia<extra></extra>"))
            medianas = por_dia.groupby("ano")["acidentes"].median()
            q3 = por_dia.groupby("ano")["acidentes"].quantile(0.75)
            # Posição pelo índice da categoria: com x="2015" o Plotly lê o número 2015
            for i, (a, med) in enumerate(medianas.items()):
                fig.add_annotation(x=i, y=q3[a], text=fmt(med), showarrow=False, yshift=10,
                                   font=dict(size=11))
            fig.update_yaxes(title_text="Acidentes por dia", showgrid=True,
                             gridcolor=c["grade"], zeroline=False)
        fig.update_xaxes(showgrid=False, type="category")
        grafico(layout(fig), chave=f"acidentes-{visao}")
with d:
    subtitulo("Mortos por ano", "Linha: tendência de queda de cerca de 6,6% ao ano.")
    with area("g2-mortos", 302):
        mortes = tabela("h3_mortes")
        fig = go.Figure(go.Bar(
            x=anos, y=anual["mortos"], marker_color=c["laranja"],
            text=anual["mortos"], textposition="outside", cliponaxis=False,
            hovertemplate="%{x}: %{y} mortos<extra></extra>"))
        fig.add_trace(go.Scatter(x=mortes["ano"].astype(str), y=mortes["ajuste"], mode="lines",
                                 line=dict(color=c["texto2"], width=2), hoverinfo="skip"))
        fig.update_yaxes(visible=False, range=[0, anual["mortos"].max() * 1.12])
        fig.update_xaxes(showgrid=False, type="category")
        grafico(texto_dentro(layout(fig)))
