import streamlit as st

from comum import (ANOS, area, barras_h, base, cores, fmt, grafico, populacao_bairros,
                   subtitulo, titulo)

df = base()
c = cores()
N = 10

titulo("Bairros e vias")
medida = st.segmented_control("Medida", ["Acidentes", "Mortos"], default="Acidentes",
                              required=True, label_visibility="collapsed")
coluna = "acidentes" if medida == "Acidentes" else "mortos"
cor = c["azul"] if medida == "Acidentes" else c["laranja"]

e, d = st.columns(2)
with e:
    t1, t2 = st.columns([1.4, 1], vertical_alignment="center")
    with t1:
        subtitulo(f"Bairros: {medida.lower()}",
                  "Bairro oficial (IBGE 2022), atribuído pelas coordenadas do acidente. "
                  "'Por habitante' divide pela população do Censo 2022 e pelos 10 anos.")
    por_hab = t2.toggle("Por habitante", key="por_hab")
    with area("g1-bairros", 226):
        b = df.groupby("bairro", observed=True).agg(acidentes=("ano", "size"),
                                                    mortos=("mortos", "sum"))
        b["populacao"] = populacao_bairros().reindex(b.index)
        if por_hab:
            escala, unidade = (1e4, "por 10 mil hab./ano") if coluna == "acidentes" \
                else (1e5, "por 100 mil hab./ano")
            b["valor"] = b[coluna] / b["populacao"] * escala / ANOS
            if coluna == "mortos":  # taxas instáveis em bairros com poucas mortes
                b = b[b["mortos"] >= 10]
            texto = lambda v: fmt(v, 1)
        else:
            b["valor"], unidade, texto = b[coluna], "", lambda v: fmt(v)
        top = b.nlargest(N, "valor")
        fig = barras_h(top.index.tolist(), top["valor"].tolist(), cor,
                       [texto(v) for v in top["valor"]],
                       hover="%{y}: %{x:,.1f} " + (unidade or medida.lower()) + "<extra></extra>")
        grafico(fig)

with d:
    subtitulo(f"Vias: {medida.lower()}",
              "Nomes de vias padronizados (abreviações, grafias e erros de digitação). "
              "CE-040 e Av. Washington Soares são o mesmo corredor e aparecem somadas.")
    with area("g1-vias", 226):
        v = df.groupby("via", observed=True).agg(acidentes=("ano", "size"),
                                                 mortos=("mortos", "sum"))
        top = v.nlargest(N, coluna)
        rotulos = [x.replace("Avenida ", "Av. ") for x in top.index]
        outra = "mortos" if coluna == "acidentes" else "acidentes"
        fig = barras_h(rotulos, top[coluna].tolist(), cor,
                       [f"{fmt(a)}  ·  {fmt(o)} {outra}" for a, o in zip(top[coluna], top[outra])],
                       hover="%{y}: %{x:,.0f} " + coluna + "<extra></extra>")
        fig.update_xaxes(range=[0, top[coluna].max() * 1.45])
        grafico(fig)
