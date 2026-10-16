import numpy as np
import plotly.graph_objects as go
import streamlit as st

from comum import VEICULOS, area, barras_h, base, cores, grafico, layout, pct, subtitulo, titulo, wilson

df = base()
c = cores()
v = df[df["veiculos_informados"]]

titulo("Veículos e tipos de acidente",
       "Só os acidentes com veículos informados (91% da base).")

e, d = st.columns(2)
with e:
    subtitulo("% dos acidentes com cada veículo",
              "Um acidente pode envolver mais de um tipo de veículo, por isso a soma passa de 100%.")
    with area("g1-presenca", 186):
        p = (100 * v[list(VEICULOS)].mean()).rename(VEICULOS).sort_values(ascending=False)
        fig = barras_h(p.index.tolist(), p.tolist(), c["azul"], [pct(x) for x in p],
                       hover="%{y}: %{x:.1f}% dos acidentes<extra></extra>")
        grafico(fig)

with d:
    t1, t2 = st.columns([1.2, 1], vertical_alignment="center")
    with t1:
        subtitulo("Letalidade",
                  "% dos acidentes que tiveram ao menos uma morte. Passe o mouse sobre a barra "
                  "para ver o intervalo de confiança de 95%.")
    por = t2.segmented_control("Por", ["Veículo", "Tipo"], default="Veículo", required=True,
                               label_visibility="collapsed")
    with area("g1-letalidade", 192):
        if por == "Veículo":
            linhas = [(nome, int(v.loc[v[col], "fatal"].sum()), int(v[col].sum()))
                      for col, nome in VEICULOS.items()]
        else:
            g = df.groupby("natureza", observed=True)["fatal"].agg(["sum", "count"])
            g = g[(g["count"] >= 500) & (g.index != "Não informado")]
            linhas = [(i, int(r["sum"]), int(r["count"])) for i, r in g.iterrows()]
        nomes, ev, n = zip(*sorted(linhas, key=lambda x: x[1] / x[2], reverse=True)[:10])
        taxa = 100 * np.array(ev) / np.array(n)
        inf, sup = wilson(ev, n)
        fig = go.Figure(go.Bar(
            x=taxa, y=list(nomes), orientation="h", marker_color=c["laranja"],
            text=[pct(t, 1) for t in taxa], textposition="outside", cliponaxis=False,
            customdata=np.column_stack([n, ev, inf, sup]),
            hovertemplate="%{y}: %{x:.2f}% (IC 95%: %{customdata[2]:.2f}% a "
                          "%{customdata[3]:.2f}%)<br>%{customdata[1]:,.0f} fatais em "
                          "%{customdata[0]:,.0f} acidentes<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix="  ")
        fig.update_xaxes(visible=False, range=[0, max(taxa) * 1.18])
        grafico(layout(fig))
