"""Download e preparo dos dados externos por bairro (IBGE Censo 2022 e OpenStreetMap)."""

import io
import urllib.request
import zipfile

import geopandas as gpd
import pandas as pd

from . import config
from .texto import normalizar


def baixar_malha_bairros():
    """Limites oficiais dos 121 bairros de Fortaleza (IBGE, Censo 2022)."""
    with urllib.request.urlopen(config.URL_MALHA_BAIRROS_CE, timeout=300) as r:
        conteudo = r.read()
    ce = gpd.read_file(io.BytesIO(conteudo))
    fortaleza = ce[ce["CD_MUN"] == config.COD_IBGE_FORTALEZA]
    fortaleza = fortaleza[["CD_BAIRRO", "NM_BAIRRO", "NM_SUBDIST", "geometry"]]
    fortaleza.to_file(config.ARQ_MALHA_BAIRROS, driver="GPKG")
    return fortaleza


def baixar_populacao_bairros():
    """População residente (v0001) e área por bairro (IBGE, Censo 2022)."""
    with urllib.request.urlopen(config.URL_POP_BAIRROS_BR, timeout=300) as r:
        conteudo = r.read()
    with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
        nome = z.namelist()[0]
        tabela = pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str)
    tabela = tabela[tabela["CD_MUN"] == config.COD_IBGE_FORTALEZA]
    pop = pd.DataFrame({
        "CD_BAIRRO": tabela["CD_BAIRRO"],
        "NM_BAIRRO": tabela["NM_BAIRRO"],
        "populacao": tabela["v0001"].astype(int),
        "area_km2": tabela["AREA_KM2"].str.replace(",", ".").astype(float),
    })
    pop.to_csv(config.ARQ_POP_BAIRROS, index=False)
    return pop


def baixar_malha_viaria(bairros):
    """Km de vias e número de cruzamentos por bairro, a partir do OpenStreetMap.

    Cruzamento = nó da malha onde se encontram 3 ou mais ruas.
    """
    import osmnx as ox

    contorno = bairros.to_crs(4326).union_all()
    grafo = ox.graph_from_polygon(contorno, network_type="drive")
    grafo = ox.convert.to_undirected(grafo)
    nos, arestas = ox.graph_to_gdfs(grafo)

    bairros_m = bairros.to_crs(31984)  # SIRGAS 2000 / UTM 24S, em metros
    nos = nos.to_crs(31984)
    arestas = arestas.to_crs(31984)

    cruzamentos = nos[nos["street_count"] >= 3]
    cruz = (
        gpd.sjoin(cruzamentos[["geometry"]], bairros_m[["CD_BAIRRO", "geometry"]],
                  predicate="within")
        .groupby("CD_BAIRRO").size().rename("cruzamentos")
    )

    # Cada trecho é atribuído ao bairro onde está o seu ponto médio
    pontos = arestas[["length", "geometry"]].copy()
    pontos["geometry"] = pontos.geometry.interpolate(0.5, normalized=True)
    km = (
        gpd.sjoin(pontos, bairros_m[["CD_BAIRRO", "geometry"]], predicate="within")
        .groupby("CD_BAIRRO")["length"].sum().div(1000).rename("km_vias")
    )

    malha = pd.concat([cruz, km], axis=1).fillna(0).reset_index()
    malha.to_csv(config.ARQ_MALHA_VIARIA, index=False)
    return malha


def carregar_bairros():
    """Malha de bairros com população, área e indicadores viários."""
    bairros = gpd.read_file(config.ARQ_MALHA_BAIRROS)
    pop = pd.read_csv(config.ARQ_POP_BAIRROS, dtype={"CD_BAIRRO": str})
    malha = pd.read_csv(config.ARQ_MALHA_VIARIA, dtype={"CD_BAIRRO": str})
    bairros = (
        bairros.merge(pop[["CD_BAIRRO", "populacao", "area_km2"]], on="CD_BAIRRO")
        .merge(malha, on="CD_BAIRRO", how="left")
    )
    bairros["bairro"] = bairros["NM_BAIRRO"]
    bairros["chave"] = bairros["NM_BAIRRO"].map(normalizar)
    return bairros


def baixar_tudo():
    config.garantir_pastas()
    bairros = baixar_malha_bairros()
    print(f"Malha de bairros: {len(bairros)} bairros")
    pop = baixar_populacao_bairros()
    print(f"População: {pop['populacao'].sum():,} habitantes")
    malha = baixar_malha_viaria(bairros)
    print(f"Malha viária: {malha['km_vias'].sum():,.0f} km, "
          f"{malha['cruzamentos'].sum():,.0f} cruzamentos")
