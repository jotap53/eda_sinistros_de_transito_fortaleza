import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from comum import (area, barras_h, celular, cores, fmt, grafico, layout, pct, resultados, tabela,
                   texto_dentro, titulo)

r = resultados()
c = cores()

titulo("Hipóteses")
h = st.segmented_control(
    "Hipótese", ["H1 · Madrugada", "H2 · Motos", "H3 · Tendência", "H4 · Controle", "H5 · Bairros"],
    default="H1 · Madrugada", required=True, label_visibility="collapsed")


def enunciado(texto, conclusao, metodo):
    st.markdown(f"**{texto}** — {conclusao}", help=metodo)


# ------------------------------------------------------------------ H1
if h.startswith("H1"):
    r1 = r["h1"]
    enunciado("Há mais mortes na madrugada do fim de semana?",
              f"Sim: {fmt(r1['razao_mortes_dia'], 2)} vez mais mortes por dia que na madrugada "
              f"de dia útil, com quase o mesmo número de acidentes.",
              "Compara a madrugada (0h-6h) de sábado e domingo com a de segunda a sexta. "
              f"Razão de taxas de Poisson: {fmt(r1['razao_mortes_dia'], 2)} (IC 95% "
              f"{fmt(r1['razao_mortes_dia_ic'][0], 2)}-{fmt(r1['razao_mortes_dia_ic'][1], 2)}). "
              f"Ajustando por veículos e ano, a chance de morte é "
              f"{fmt(r1['or_madrugada_ajustado'], 2)} vez maior.")
    m = tabela("h1_mortes_por_dia")
    madr = m[m["faixa_horaria"] == "Madrugada"].set_index("fim_de_semana")
    medidas = [
        ("Acidentes por dia", madr["acidentes_dia"], lambda v: fmt(v, 1)),
        ("Mortos a cada 100 dias", madr["mortos_100_dias"], lambda v: fmt(v, 1)),
        ("Letalidade (%)", [r1["letalidade_madrugada_util"], r1["letalidade_madrugada_fds"]],
         lambda v: pct(v, 2)),
    ]
    estreito = celular()
    grupos = ["Útil", "Fim de<br>semana"] if estreito else ["Dia útil", "Fim de semana"]
    with area("g1-h1", 256):
        fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08,
                            subplot_titles=[x[0].replace(" ", "<br>", 1) if estreito else x[0]
                                            for x in medidas])
        for i, (nome, valores, f) in enumerate(medidas, start=1):
            valores = list(valores) if not hasattr(valores, "loc") else [valores.loc[False],
                                                                         valores.loc[True]]
            fig.add_bar(x=grupos, y=valores,
                        marker_color=[c["azul"], c["laranja"]], text=[f(v) for v in valores],
                        textposition="outside", cliponaxis=False, row=1, col=i,
                        hovertemplate="%{x}: %{text}<extra>" + nome + "</extra>")
            fig.update_yaxes(visible=False, range=[0, max(valores) * 1.2], row=1, col=i)
        fig.update_xaxes(showgrid=False)
        grafico(layout(fig, margem=dict(t=56 if estreito else 34)))

# ------------------------------------------------------------------ H2
elif h.startswith("H2"):
    r2 = r["h2"]
    enunciado("Acidentes com moto têm mais vítimas?",
              f"Sim: {pct(r2['pct_com_vitima_moto'])} têm vítima, contra "
              f"{pct(r2['pct_com_vitima_sem_moto'])} sem moto.",
              "Só acidentes com veículos informados. Regressão de Poisson (erros robustos, "
              "ajustada por ano): o número médio de vítimas é "
              f"{fmt(100 * (r2['irr']['Só moto']['irr'] - 1))}% maior em acidentes só com moto "
              "que em acidentes só com automóveis.")
    p = tabela("h2_pct_com_vitima")
    p = p[p["n"] >= 1000].sort_values("pct", ascending=False)
    with area("g1-h2", 256):
        fig = barras_h(p["perfil_veiculos"].tolist(), p["pct"].tolist(), c["azul"],
                       [pct(v, 0) for v in p["pct"]],
                       destaque=["Só moto", "Moto + automóvel"], cor_destaque=c["laranja"],
                       hover="%{y}: %{x:.1f}% com vítima<extra></extra>")
        fig.update_xaxes(range=[0, 115])
        grafico(fig)

# ------------------------------------------------------------------ H3
elif h.startswith("H3"):
    r3 = r["h3"]
    enunciado("Os acidentes caem ao longo do tempo?",
              f"Não de forma gradual: caem de patamar em jan/2018. As mortes, sim: "
              f"{pct(r3['mortes_variacao_anual_pct'], 1)} ao ano.",
              f"Teste de Chow em todos os meses: a quebra está em jan/2018 (F = "
              f"{fmt(r3['quebra_F'], 0)}). Modelo com dois patamares, sazonalidade e efeito da "
              f"pandemia: R² {fmt(r3['r2_segmentado'], 2)}, contra {fmt(r3['r2_linear'], 2)} de "
              "uma reta única. A queda se concentra em acidentes sem vítima, o que indica "
              "mudança no registro.")
    s = tabela("h3_serie")
    mt = tabela("h3_mortes")
    e, d = st.columns([1.7, 1])
    with e, area("g1-h3a", 256):
        fig = go.Figure()
        fig.add_vrect(x0="2020-03-01", x1="2020-12-31", fillcolor=c["cinza"], opacity=0.25,
                      line_width=0, annotation_text="pandemia", annotation_position="top left")
        fig.add_scatter(x=s["data"], y=s["acidentes"], mode="lines", name="Acidentes por mês",
                        line=dict(color=c["cinza"], width=1.3),
                        hovertemplate="%{x|%m/%Y}: %{y:,.0f}<extra></extra>")
        fig.add_scatter(x=s["data"], y=s["ajuste_segmentado"], mode="lines",
                        name="Modelo (dois patamares)", line=dict(color=c["azul"], width=2.2),
                        hoverinfo="skip")
        fig.update_yaxes(title_text="Acidentes por mês", tickformat=",.0f")
        fig.update_xaxes(showgrid=False)
        grafico(layout(fig, legenda=True, margem=dict(t=30)))
    with d, area("g1-h3b", 256):
        fig = go.Figure(go.Bar(x=mt["ano"].astype(str), y=mt["mortos"], marker_color=c["laranja"],
                               text=mt["mortos"], textposition="outside", cliponaxis=False,
                               hovertemplate="%{x}: %{y} mortos<extra></extra>", name="Mortos"))
        fig.add_scatter(x=mt["ano"].astype(str), y=mt["ajuste"], mode="lines",
                        line=dict(color=c["texto2"], width=2), hoverinfo="skip", name="Tendência")
        fig.update_yaxes(visible=False, range=[0, mt["mortos"].max() * 1.18])
        fig.update_xaxes(showgrid=False, type="category", tickangle=0,
                         ticktext=[f"'{a % 100:02d}" for a in mt["ano"]],
                         tickvals=mt["ano"].astype(str))
        fig.update_layout(title=dict(text="Mortos por ano", x=0, font_size=13))
        grafico(layout(fig, margem=dict(t=34)))

# ------------------------------------------------------------------ H4
elif h.startswith("H4"):
    r4 = r["h4"]
    o = r4["or"]["Sem controle (vs. semáforo)"]
    enunciado("O controle de tráfego influencia a gravidade?",
              f"Pouco em geral (V = {fmt(r4['v_cramer_sem_ni'], 2)}), mas sem controle a chance "
              f"de morte é {fmt(o['or'], 2)} vez a de um semáforo.",
              f"Só os {fmt(r4['n_sem_ni'])} acidentes (39%) com o controle informado. Regressão "
              f"logística ajustada por horário, dia e ano: sem controle vs. semáforo OR "
              f"{fmt(o['or'], 2)} (IC {fmt(o['ic'][0], 2)}-{fmt(o['ic'][1], 2)}). Com o 'não "
              f"informado' tratado como categoria, o V subiria para "
              f"{fmt(r4['v_cramer_com_ni'], 2)}, mas por causa do preenchimento.")
    t = tabela("h4_letalidade").sort_values("pct", ascending=False)
    with area("g1-h4", 256):
        fig = go.Figure(go.Bar(
            x=t["pct"], y=t["controle_trafego"], orientation="h",
            marker_color=[c["laranja"] if x == "Sem controle" else c["azul"]
                          for x in t["controle_trafego"]],
            error_x=dict(type="data", symmetric=False, array=t["ic_sup"] - t["pct"],
                         arrayminus=t["pct"] - t["ic_inf"], color=c["texto2"], thickness=1,
                         width=0),
            text=[pct(v, 2) for v in t["pct"]], textposition="outside", cliponaxis=False,
            customdata=t[["n"]],
            hovertemplate="%{y}: %{x:.2f}% fatais (%{customdata[0]:,.0f} acidentes)"
                          "<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix="  ")
        fig.update_xaxes(visible=False, range=[0, t["ic_sup"].max() * 1.08])
        grafico(texto_dentro(layout(fig)))

# ------------------------------------------------------------------ H5
else:
    r5 = r["h5"]
    enunciado("População e malha viária explicam os acidentes por bairro?",
              f"Em parte (cerca de {fmt(100 * r5['pseudo_r2']['População + km de vias'])}%): "
              "polos de comércio e passagem ficam bem acima do esperado.",
              "Binomial Negativa com dados externos: população (IBGE, Censo 2022) e km de vias "
              "(OpenStreetMap). Pontos acima da linha têm mais acidentes do que o esperado para "
              "sua população e malha viária. Tamanho do ponto = população.")
    b = tabela("h5_bairros")
    destaque = set(b.nlargest(5, "razao_obs_esp")["bairro"]) | set(
        b.nsmallest(2, "razao_obs_esp")["bairro"])
    with area("g1-h5", 256):
        lim = [b[["esperado", "acidentes"]].min().min() * 0.8,
               b[["esperado", "acidentes"]].max().max() * 1.25]
        fig = go.Figure()
        fig.add_scatter(x=lim, y=lim, mode="lines", line=dict(color=c["texto2"], width=1),
                        hoverinfo="skip")
        cor_pontos = [c["laranja"] if x in destaque else c["azul"] for x in b["bairro"]]
        fig.add_scatter(
            x=b["esperado"], y=b["acidentes"], mode="markers+text",
            text=[f"{x} ({fmt(rz, 1)}×)" if x in destaque else "" for x, rz in
                  zip(b["bairro"], b["razao_obs_esp"])],
            textposition="middle right", textfont=dict(size=11),
            marker=dict(size=np.sqrt(b["populacao"]) / 14 + 4, color=cor_pontos, opacity=0.7,
                        line=dict(width=0)),
            customdata=np.column_stack([b["bairro"], b["razao_obs_esp"]]),
            hovertemplate="%{customdata[0]}<br>Observado: %{y:,.0f}<br>Esperado: %{x:,.0f}"
                          "<br>%{customdata[1]:.1f}× o esperado<extra></extra>")
        fig.update_xaxes(type="log", title_text="Acidentes esperados (população e km de vias)",
                         tickformat=",.0f")
        fig.update_yaxes(type="log", title_text="Acidentes observados", tickformat=",.0f")
        grafico(layout(fig))
