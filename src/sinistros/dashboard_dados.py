"""Dados prontos para o dashboard (dashboard/).

O dashboard roda no Streamlit Community Cloud só com pandas, plotly e pydeck.
Aqui geramos, a partir das análises, o que exige bibliotecas mais pesadas
(geopandas, statsmodels): a malha dos bairros em GeoJSON e as tabelas das
hipóteses. Tudo vai para dashboard/dados/.
"""

import json

import numpy as np
import pandas as pd

from . import analises, config
from .externos import carregar_bairros

PASTA = config.RAIZ / "dashboard" / "dados"

COLUNAS_BASE = [
    "data", "ano", "hora", "dia_semana", "fim_de_semana", "faixa_horaria", "bairro", "via",
    "latitude", "longitude", "natureza", "controle_trafego", "severidade", "fatal", "mortos",
    "feridos", "vitimas", "veiculos_informados", "perfil_veiculos",
]


def _base(df):
    """Base enxuta: só as colunas usadas no dashboard, com tipos compactos."""
    b = df[COLUNAS_BASE].copy()
    b["latitude"] = b["latitude"].astype("float32")
    b["longitude"] = b["longitude"].astype("float32")
    for col in ("ano", "hora", "mortos", "feridos", "vitimas"):
        b[col] = b[col].astype("int16")
    for col in ("bairro", "via"):
        b[col] = b[col].astype("category")
    # Presença de cada tipo de veículo (vazio quando os veículos não foram informados)
    for nome, colunas in {"automovel": ["automovel"], "moto": ["motocicleta", "ciclomotor"],
                          "onibus": ["onibus", "microonibus"], "caminhao": ["caminhao"],
                          "bicicleta": ["bicicleta"]}.items():
        b[f"v_{nome}"] = (df[colunas].sum(axis=1) > 0) & df["veiculos_informados"]
    return b


def _geojson_bairros():
    b = carregar_bairros().to_crs(4326)
    b["geometry"] = b.geometry.simplify(0.0003, preserve_topology=True)
    b = b[["CD_BAIRRO", "bairro", "populacao", "km_vias", "geometry"]]
    return json.loads(b.to_json())


def exportar(df, resultados):
    PASTA.mkdir(parents=True, exist_ok=True)
    _base(df).to_parquet(PASTA / "sinistros.parquet", index=False)

    with open(PASTA / "bairros.geojson", "w", encoding="utf-8") as f:
        json.dump(_geojson_bairros(), f, ensure_ascii=False)

    # Hipóteses: tabelas que dependem de modelos estatísticos
    h1 = analises.h1_madrugada_fim_de_semana(df)
    h1["mortes_por_dia"].assign(faixa_horaria=lambda d: d["faixa_horaria"].astype(str)) \
        .to_parquet(PASTA / "h1_mortes_por_dia.parquet", index=False)

    h2 = analises.h2_motos_feridos(df)
    h2["pct_com_vitima"].reset_index().assign(
        perfil_veiculos=lambda d: d["perfil_veiculos"].astype(str)
    ).to_parquet(PASTA / "h2_pct_com_vitima.parquet", index=False)

    h3 = analises.h3_tendencia(df)
    h3["serie"].reset_index(names="data").to_parquet(PASTA / "h3_serie.parquet", index=False)
    h3["mortes_anuais"].to_parquet(PASTA / "h3_mortes.parquet", index=False)

    h4 = analises.h4_controle_trafego(df)
    h4["letalidade"].reset_index().assign(
        controle_trafego=lambda d: d["controle_trafego"].astype(str)
    ).to_parquet(PASTA / "h4_letalidade.parquet", index=False)

    h5 = analises.h5_bairros(df)
    h5["bairros"][["bairro", "acidentes", "esperado", "razao_obs_esp", "populacao"]] \
        .to_parquet(PASTA / "h5_bairros.parquet", index=False)

    resumo = {k: resultados[k] for k in ("passo1", "h1", "h2", "h3", "h4", "h5")}
    with open(PASTA / "resultados.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return PASTA


if __name__ == "__main__":
    from . import limpeza
    with open(config.ARQ_RESULTADOS, encoding="utf-8") as f:
        res = json.load(f)
    print(exportar(limpeza.carregar(), res))
