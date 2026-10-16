"""Mapas interativos (Folium), com as coordenadas reais dos acidentes.

Substituem o mapa da versão anterior, que usava coordenadas aproximadas
digitadas à mão para cada via.
"""

import folium
import geopandas as gpd
import numpy as np
from branca.colormap import LinearColormap
from folium.plugins import HeatMap

from . import config

CENTRO_FORTALEZA = (-3.7700, -38.5300)
CORES_VIAS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
              "#6250d6", "#e34948"]


def mapa_interativo(df, bairros, ranking_vias, n_vias=8, arquivo="mapa_interativo.html"):
    """Um mapa com três camadas que podem ser ligadas e desligadas:

    - mapa de calor de todos os acidentes;
    - bairros coloridos por acidentes por 10 mil habitantes por ano;
    - acidentes das `n_vias` vias com mais registros, um ponto por acidente.
    """
    m = folium.Map(location=CENTRO_FORTALEZA, zoom_start=12, tiles="CartoDB positron",
                   control_scale=True)

    # Camada 1: mapa de calor
    pontos = np.round(df[["latitude", "longitude"]].dropna().to_numpy(), 4).tolist()
    HeatMap(pontos, name="Mapa de calor (todos os acidentes)", radius=7, blur=9,
            min_opacity=0.25).add_to(m)

    # Camada 2: bairros por taxa
    b = bairros.to_crs(4326).copy()
    b["geometry"] = b.geometry.simplify(0.0002)
    escala = LinearColormap(["#f3f7fd", "#9ec5f4", "#3987e5", "#184f95", "#0d366b"],
                            vmin=0, vmax=float(b["acidentes_10k_hab_ano"].quantile(0.98)),
                            caption="Acidentes por 10 mil habitantes por ano")
    campos = b[["bairro", "acidentes", "populacao", "acidentes_10k_hab_ano", "mortos",
                "mortos_100k_hab_ano", "geometry"]].copy()
    campos["acidentes_10k_hab_ano"] = campos["acidentes_10k_hab_ano"].round(1)
    campos["mortos_100k_hab_ano"] = campos["mortos_100k_hab_ano"].round(1)
    folium.GeoJson(
        campos.to_json(), name="Bairros: acidentes por habitante", show=False,
        style_function=lambda f: {
            "fillColor": escala(min(f["properties"]["acidentes_10k_hab_ano"], escala.vmax)),
            "color": "#ffffff", "weight": 0.6, "fillOpacity": 0.75},
        tooltip=folium.GeoJsonTooltip(
            fields=["bairro", "acidentes", "populacao", "acidentes_10k_hab_ano", "mortos",
                    "mortos_100k_hab_ano"],
            aliases=["Bairro", "Acidentes (2015-2024)", "População (2022)",
                     "Acidentes / 10 mil hab. / ano", "Mortos", "Mortos / 100 mil hab. / ano"]),
    ).add_to(m)
    escala.add_to(m)

    # Camada 3: vias com mais acidentes
    for cor, (via, linha) in zip(CORES_VIAS, ranking_vias.head(n_vias).iterrows()):
        d = df[df["via"] == via]
        pontos_via = gpd.GeoDataFrame(
            {"data": d["data"].dt.strftime("%d/%m/%Y"), "hora": d["hora"].astype(str) + "h",
             "natureza": d["natureza"].astype(str),
             "severidade": d["severidade"].astype(str).replace("nan", "Sem informação"),
             "fatal": d["fatal"]},
            geometry=gpd.points_from_xy(d["longitude"].round(5), d["latitude"].round(5)),
            crs=4326)
        nome = f"{via}: {linha['acidentes']:,} acidentes, {linha['mortos']} mortos"
        folium.GeoJson(
            pontos_via.to_json(), name=nome.replace(",", "."),
            marker=folium.CircleMarker(radius=3, weight=0, fill=True),
            style_function=lambda f, cor=cor: {
                "fillColor": cor, "radius": 5 if f["properties"]["fatal"] else 2.5,
                "fillOpacity": 0.95 if f["properties"]["fatal"] else 0.5},
            tooltip=folium.GeoJsonTooltip(fields=["data", "hora", "natureza", "severidade"],
                                          aliases=["Data", "Hora", "Natureza", "Severidade"]),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    config.MAPAS.mkdir(parents=True, exist_ok=True)
    caminho = config.MAPAS / arquivo
    m.save(caminho)
    return m, caminho
