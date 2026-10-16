import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from comum import (FAIXAS, VEICULOS, area, base, celular, cores, escuro, filtrar, fmt,
                   geojson_bairros, pct, populacao_bairros, titulo)

df = base()
c = cores()

MAX_PONTOS = 40_000  # acima disso, amostra (os acidentes fatais entram sempre)


def rgb(hexa, alfa=255):
    hexa = hexa.lstrip("#")
    return [int(hexa[i:i + 2], 16) for i in (0, 2, 4)] + [alfa]


def limpar():
    for k in list(st.session_state):
        if k.startswith("f_"):
            del st.session_state[k]


titulo("Mapa", "Cada ponto é um acidente, na coordenada registrada. Use os filtros para "
               "recortar por período, horário, gravidade, veículo, tipo de acidente e bairro.")

# ------------------------------------------------------------------ Controles
cf, cv, cn = st.columns([1, 2.2, 3], vertical_alignment="center")
with cf.popover("Filtros", icon=":material/tune:", use_container_width=True):
    anos = st.slider("Período", 2015, 2024, (2015, 2024), key="f_anos")
    dias = st.segmented_control("Dias", ["Todos", "Dias úteis", "Fim de semana"],
                                default="Todos", required=True, key="f_dias")
    faixas = st.pills("Faixa horária", FAIXAS, selection_mode="multi", key="f_faixas",
                      help="Madrugada 0h-6h · Manhã 6h-12h · Tarde 12h-18h · Noite 18h-24h. "
                           "Nenhuma marcada = todas.")
    severidade = st.segmented_control("Gravidade", ["Todos", "Com vítima", "Fatais"],
                                      default="Todos", required=True, key="f_sev")
    veiculos = st.pills("Veículo envolvido", list(VEICULOS.values()), selection_mode="multi",
                        key="f_veic", help="Acidentes com ao menos um dos veículos marcados.")
    naturezas = st.multiselect("Tipo de acidente", sorted(df["natureza"].cat.categories),
                               key="f_nat", placeholder="Todos")
    bairros = st.multiselect("Bairro", sorted(df["bairro"].dropna().unique()), key="f_bairro",
                             placeholder="Todos")
    st.button("Limpar filtros", on_click=limpar, icon=":material/restart_alt:",
              use_container_width=True)

modo = cv.segmented_control("Visualização", ["Pontos", "Calor", "Bairros"], default="Pontos",
                            required=True, label_visibility="collapsed", key="modo")

d = filtrar(df, anos, dias, faixas, severidade, veiculos, naturezas, bairros)
n, mortos = len(d), int(d["mortos"].sum())
letal = 100 * d["fatal"].mean() if n else 0
contador = f"**{fmt(n)}** acidentes · **{fmt(mortos)}** mortos · letalidade **{pct(letal, 2)}**"

# ------------------------------------------------------------------ Camadas
vista = pdk.ViewState(latitude=-3.79, longitude=-38.53, zoom=10.0 if celular() else 11.0, pitch=0)
# Contorno dos bairros por baixo de tudo: referência geográfica mesmo sem o fundo de ruas
contorno = (255, 255, 255, 70) if escuro() else (90, 90, 85, 70)
camadas = [pdk.Layer("GeoJsonLayer", geojson_bairros(), stroked=True, filled=True,
                     get_fill_color=[128, 128, 128, 12], get_line_color=list(contorno),
                     line_width_min_pixels=0.7, pickable=False)]
dica, explicacao = None, None

if n == 0:
    st.info("Nenhum acidente com esses filtros.")
elif modo == "Pontos":
    fatais = d[d["fatal"]]
    outros = d[~d["fatal"]]
    if len(outros) > MAX_PONTOS - len(fatais):
        outros = outros.sample(max(MAX_PONTOS - len(fatais), 0), random_state=0)
    pts = pd.concat([outros, fatais])
    pts = pd.DataFrame({
        "lon": pts["longitude"].round(5), "lat": pts["latitude"].round(5),
        "fatal": pts["fatal"].to_numpy(),
        "data": pts["data"].dt.strftime("%d/%m/%Y").to_numpy(),
        "hora": pts["hora"].astype(str).to_numpy() + "h",
        "via": pts["via"].astype(str).replace("nan", "-").to_numpy(),
        "natureza": pts["natureza"].astype(str).to_numpy(),
        "vitimas": pts["vitimas"].to_numpy(), "mortos": pts["mortos"].to_numpy(),
    })
    pts["cor"] = [rgb(c["laranja"], 230) if f else rgb(c["azul"], 110) for f in pts["fatal"]]
    pts["raio"] = np.where(pts["fatal"], 45, 18)
    camadas.append(pdk.Layer(
        "ScatterplotLayer", pts, get_position=["lon", "lat"], get_fill_color="cor",
        get_radius="raio", radius_min_pixels=1.2, radius_max_pixels=9, pickable=True))
    dica = {"html": "<b>{data}</b>, {hora}<br>{natureza}<br>{via}<br>"
                    "Vítimas: {vitimas} · Mortos: {mortos}"}
    explicacao = "Azul: acidente. Laranja: acidente com morte."
    if len(d) > MAX_PONTOS:
        explicacao += (f" O mapa mostra {fmt(len(pts))} dos {fmt(n)} acidentes (amostra "
                       f"aleatória; todos os fatais aparecem). Filtre para ver todos.")

elif modo == "Calor":
    grade = (d.assign(lat=d["latitude"].round(3), lon=d["longitude"].round(3))
             .groupby(["lat", "lon"]).size().reset_index(name="peso"))
    camadas.append(pdk.Layer(
        "HeatmapLayer", grade, get_position=["lon", "lat"], get_weight="peso",
        radius_pixels=28, intensity=1.1, threshold=0.04,
        color_range=[rgb(x)[:3] for x in c["rampa"][1:]] + [rgb(c["laranja"])[:3]]))
    explicacao = "Concentração de acidentes: quanto mais intensa a cor, mais acidentes na área."

else:  # Bairros
    contagem = d.groupby("bairro", observed=True).agg(acidentes=("ano", "size"),
                                                      mortos=("mortos", "sum"))
    pop = populacao_bairros()
    anos_periodo = anos[1] - anos[0] + 1
    taxa = (contagem["acidentes"] / pop.reindex(contagem.index) * 1e4 / anos_periodo).fillna(0)
    maximo = max(float(taxa.quantile(0.97)), 1e-9)
    rampa = [rgb(x) for x in c["rampa"]]
    geo = geojson_bairros()
    for f in geo["features"]:
        nome = f["properties"]["bairro"]
        t = float(taxa.get(nome, 0))
        i = min(int(t / maximo * (len(rampa) - 1) + 0.5), len(rampa) - 1)
        f["properties"].update({
            "cor": rampa[i][:3] + [210], "taxa": fmt(t, 1),
            "acidentes": fmt(contagem["acidentes"].get(nome, 0)),
            "mortos": int(contagem["mortos"].get(nome, 0)),
            "pop": fmt(f["properties"]["populacao"]),
        })
    camadas.append(pdk.Layer(
        "GeoJsonLayer", geo, get_fill_color="properties.cor", get_line_color=[255, 255, 255, 90],
        line_width_min_pixels=0.6, pickable=True, auto_highlight=True))
    dica = {"html": "<b>{bairro}</b><br>{acidentes} acidentes · {mortos} mortos<br>"
                    "{taxa} acidentes por 10 mil hab./ano<br>População: {pop}"}
    explicacao = ("Cor: acidentes por 10 mil habitantes por ano no período filtrado "
                  "(mais intensa = mais acidentes). População: IBGE, Censo 2022.")

cn.markdown(contador, help=explicacao)

with area("mapa", 200, celular="calc(100dvh - 320px)"):
    # map_style=None: o Streamlit escolhe o fundo de ruas (Carto) conforme o tema
    st.pydeck_chart(pdk.Deck(layers=camadas, initial_view_state=vista, map_style=None,
                             tooltip=dica), height="stretch")
