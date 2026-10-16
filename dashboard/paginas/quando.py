import plotly.graph_objects as go
import streamlit as st

from comum import (DIAS, FAIXAS, FAIXAS_ROTULO, area, base, cores, fmt, grafico, layout,
                   subtitulo, tabela, titulo)

df = base()
c = cores()

titulo("Quando acontecem")

e, d = st.columns([1.35, 1])
with e:
    subtitulo("Acidentes por dia, em cada hora",
              "Média de acidentes por dia em cada hora e dia da semana (2015-2024). "
              "Passe o mouse sobre as células para ver os valores.")
    with area("g1-calor", 186):
        dias = df.groupby("dia_semana", observed=True)["data"].nunique()
        tab = (df.groupby(["dia_semana", "hora"], observed=True).size().unstack()
               .div(dias, axis=0).reindex(DIAS))
        fig = go.Figure(go.Heatmap(
            z=tab.values, x=[f"{h}h" for h in tab.columns], y=tab.index,
            colorscale=c["rampa"], showscale=False, xgap=1.5, ygap=1.5,
            hovertemplate="%{y}, %{x}: %{z:.1f} acidentes por dia<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=False, tickangle=0, dtick=3)
        grafico(layout(fig))

with d:
    subtitulo("Mortos a cada 100 dias",
              "Na madrugada (0h-6h), o fim de semana tem quase o mesmo número de acidentes por "
              "dia que os dias úteis, mas 1,7 vez mais mortes: os acidentes são mais graves.")
    with area("g1-mortes", 186):
        m = tabela("h1_mortes_por_dia")
        fig = go.Figure()
        for fds, nome, cor in [(False, "Dia útil", c["azul"]), (True, "Fim de semana", c["laranja"])]:
            s = m[m["fim_de_semana"] == fds].set_index("faixa_horaria").reindex(FAIXAS)
            fig.add_bar(x=[FAIXAS_ROTULO[f] for f in FAIXAS], y=s["mortos_100_dias"], name=nome,
                        marker_color=cor, text=[fmt(v, 1) for v in s["mortos_100_dias"]],
                        textposition="outside", cliponaxis=False,
                        customdata=s[["mortos", "dias"]],
                        hovertemplate=nome + ": %{y:.1f} mortos a cada 100 dias"
                                      "<br>(%{customdata[0]} mortos em %{customdata[1]:,.0f} dias)"
                                      "<extra></extra>")
        fig.update_yaxes(visible=False, range=[0, m["mortos_100_dias"].max() * 1.2])
        fig.update_xaxes(showgrid=False)
        grafico(layout(fig, legenda=True, margem=dict(t=30)))
