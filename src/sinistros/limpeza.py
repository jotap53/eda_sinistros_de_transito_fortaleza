"""Limpeza e enriquecimento da base de sinistros.

Cada decisão de tratamento fica registrada em um log (etapa, linhas afetadas,
descrição), salvo junto com a base tratada.
"""

import geopandas as gpd
import numpy as np
import pandas as pd

from . import config
from .externos import carregar_bairros
from .texto import normalizar, numero_br, pct_br
from .vias import padronizar_vias

ROTULOS = {
    "tipocruzamento": {
        "meio de quadra": "Meio de quadra", "cruzamento": "Cruzamento", "t": "T",
        "duplo t": "Duplo T", "rotatória": "Rotatória", "y": "Y",
        "com via férrea": "Com via férrea",
    },
    "controletrafego": {
        "pare": "Pare", "semáforo": "Semáforo", "não há controle": "Sem controle",
        "gesto": "Gesto (agente)", "dê preferência": "Dê a preferência",
        "cancela": "Cancela", "faixa de pedestre": "Faixa de pedestre",
    },
    "usosolo": {"longo da via": "Ao longo da via", "cruzamento": "Cruzamento"},
}

# Nomes de bairro da base original que diferem da malha do IBGE
BAIRROS_EQUIVALENTES = {"tauape": "sao joao do tauape"}


class Log:
    def __init__(self):
        self.linhas = []

    def registrar(self, etapa, afetadas, descricao, linhas_resultantes):
        self.linhas.append({
            "etapa": etapa, "linhas_afetadas": int(afetadas),
            "linhas_resultantes": int(linhas_resultantes), "descricao": descricao,
        })

    def tabela(self):
        return pd.DataFrame(self.linhas)


def _categoria(serie, rotulos=None, ordem=None):
    s = serie.str.strip().str.lower()
    nao_inf = s.eq("não informado") | s.isna()
    if rotulos:
        s = s.map(rotulos).fillna(s.str.capitalize())
    else:
        s = s.str.capitalize()
    s = s.where(~nao_inf, config.NAO_INFORMADO)
    if ordem is None:
        ordem = s[s != config.NAO_INFORMADO].value_counts().index.tolist()
    return pd.Categorical(s, categories=list(ordem) + [config.NAO_INFORMADO])


def _severidade_pelas_contagens(df):
    """Severidade recalculada a partir das contagens de vítimas.

    Fatal se houve morto; Ferido se houve ferido; Ileso se só houve ilesos.
    Sem nenhuma pessoa contabilizada, a severidade é desconhecida (NaN).
    """
    sev = np.select(
        [df["mortos"] > 0, df["feridos"] > 0, df["ilesos"] > 0],
        ["Fatal", "Ferido", "Ileso"],
        default=None,
    )
    return pd.Categorical(sev, categories=["Ileso", "Ferido", "Fatal"], ordered=True)


def _perfil_veiculos(df):
    """Perfil dos veículos envolvidos (só para acidentes com veículos informados)."""
    moto = (df["motocicleta"] + df["ciclomotor"]) > 0
    auto = df["automovel"] > 0
    pesado = (df["onibus"] + df["caminhao"] + df["microonibus"]) > 0
    bike = df["bicicleta"] > 0
    perfil = np.select(
        [~df["veiculos_informados"], bike, pesado, moto & auto, moto, auto],
        [None, "Envolve bicicleta", "Envolve ônibus/caminhão", "Moto + automóvel",
         "Só moto", "Só automóvel"],
        default="Outros",
    )
    ordem = ["Só automóvel", "Só moto", "Moto + automóvel", "Envolve bicicleta",
             "Envolve ônibus/caminhão", "Outros"]
    return pd.Categorical(perfil, categories=ordem)


def atribuir_bairros(df, bairros, tolerancia_m=300):
    """Bairro oficial (IBGE 2022) de cada acidente, pelas coordenadas.

    Pontos que caem um pouco fora dos polígonos (orla, divisas) recebem o
    bairro mais próximo, até `tolerancia_m` metros. Retorna (nome, código,
    quantos foram recuperados pela tolerância).
    """
    pontos = gpd.GeoDataFrame(
        df[[]], geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs=4326
    ).to_crs(31984)
    poligonos = bairros[["CD_BAIRRO", "NM_BAIRRO", "geometry"]].to_crs(31984)
    juntado = gpd.sjoin(pontos, poligonos, how="left", predicate="within")
    juntado = juntado[~juntado.index.duplicated(keep="first")]

    fora = juntado["CD_BAIRRO"].isna()
    proximos = gpd.sjoin_nearest(pontos[fora], poligonos, how="inner",
                                 max_distance=tolerancia_m)
    proximos = proximos[~proximos.index.duplicated(keep="first")]
    juntado.loc[proximos.index, ["CD_BAIRRO", "NM_BAIRRO"]] = (
        proximos[["CD_BAIRRO", "NM_BAIRRO"]].values)
    return juntado["NM_BAIRRO"], juntado["CD_BAIRRO"], len(proximos)


def tratar(caminho=config.ARQ_BRUTO):
    """Lê a base bruta e devolve (base tratada, log, mapeamento de vias)."""
    log = Log()
    bruto = pd.read_csv(caminho, low_memory=False)
    log.registrar("Leitura", len(bruto),
                  "Base recebida da etapa de ETL anterior (3 registros sem código "
                  "do acidente já tinham sido removidos lá: 130.823 -> 130.820).",
                  len(bruto))

    # Duplicatas exatas: mesma data, hora, coordenada, via, natureza, vítimas e veículos
    dup = bruto.duplicated()
    bruto = bruto[~dup].reset_index(drop=True)
    log.registrar("Duplicatas", dup.sum(),
                  "Linhas idênticas em todas as 27 colunas removidas (mantida 1 cópia).",
                  len(bruto))

    df = pd.DataFrame(index=bruto.index)

    # --- Tempo
    df["data"] = pd.to_datetime(bruto["data"])
    df["hora"] = bruto["horaint"].astype(int)
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["dia_semana"] = pd.Categorical.from_codes(df["data"].dt.dayofweek, config.DIAS,
                                                 ordered=True)
    df["fim_de_semana"] = df["data"].dt.dayofweek >= 5
    df["faixa_horaria"] = pd.cut(df["hora"], bins=[0, 6, 12, 18, 24], right=False,
                                 labels=config.FAIXAS)
    df["madrugada"] = df["faixa_horaria"] == "Madrugada"
    divergentes = ((bruto["fimdesemana"] == "sim") != df["fim_de_semana"]).sum() + (
        bruto["faixahoraria"].str.split(":").str[0] != df["faixa_horaria"].astype(str)
    ).sum()
    log.registrar("Tempo", divergentes,
                  f"Dia da semana, fim de semana e faixa horária recalculados a partir da "
                  f"data e da hora e conferidos contra as colunas originais: "
                  f"{numero_br(divergentes)} divergências.", len(df))

    # --- Local
    df["latitude"] = bruto["latitude"]
    df["longitude"] = bruto["longitude"]
    bairros = carregar_bairros()
    df["bairro"], df["cd_bairro"], recuperados = atribuir_bairros(df, bairros)
    df["bairro_original"] = bruto["bairro"]
    fora = df["bairro"].isna().sum()
    original = bruto["bairro"].map(normalizar).replace(BAIRROS_EQUIVALENTES)
    concorda = (original == df["bairro"].map(normalizar)).mean()
    log.registrar("Bairro", fora,
                  f"Bairro reatribuído pelas coordenadas com a malha oficial do IBGE "
                  f"(Censo 2022, 121 bairros); {numero_br(recuperados)} pontos na orla ou nas "
                  f"divisas receberam o bairro mais próximo (até 300 m). Concordância "
                  f"com o bairro original: {pct_br(concorda)}. Linhas afetadas = pontos "
                  f"fora do município, que ficam sem bairro.", len(df))

    df["rua_original"] = bruto["rua"]
    df["via"], mapeamento_vias = padronizar_vias(bruto["rua"])
    log.registrar("Vias", bruto["rua"].nunique() - df["via"].nunique(),
                  f"Nomes de via padronizados: {numero_br(bruto['rua'].nunique())} grafias -> "
                  f"{numero_br(df['via'].nunique())} vias (abreviações, acentos, complementos, "
                  f"grafias sem tipo, erros de digitação e nomes diferentes do mesmo corredor, "
                  f"como CE-040 e Av. Washington Soares). Linhas afetadas = grafias "
                  f"unificadas. Mapeamento salvo em vias_mapeamento_nomes.csv.", len(df))

    # --- Características do local e do sinistro
    df["tipo_cruzamento"] = _categoria(bruto["tipocruzamento"], ROTULOS["tipocruzamento"])
    df["controle_trafego"] = _categoria(bruto["controletrafego"], ROTULOS["controletrafego"])
    df["uso_solo"] = _categoria(bruto["usosolo"], ROTULOS["usosolo"])
    df["natureza"] = _categoria(bruto["natureza"])
    for col in ["tipo_cruzamento", "controle_trafego", "uso_solo", "natureza"]:
        n = (df[col] == config.NAO_INFORMADO).sum()
        log.registrar("Categorias", n,
                      f"'{col}': rótulos padronizados; 'não informado' mantido como "
                      f"categoria própria e excluído nos testes ({pct_br(n / len(df))}).",
                      len(df))

    # --- Vítimas e severidade
    for col in ["mortos", "feridos", "ilesos"]:
        df[col] = bruto[col].astype(int)
    df["vitimas"] = df["mortos"] + df["feridos"]
    df["severidade_registrada"] = _categoria(bruto["severidade"],
                                             ordem=["Ileso", "Ferido", "Fatal"])
    df["severidade"] = _severidade_pelas_contagens(df)
    reg = df["severidade_registrada"].astype(str)
    calc = df["severidade"].astype(str)
    corrigidas = ((reg != calc) & (reg != config.NAO_INFORMADO)).sum()
    preenchidas = ((reg == config.NAO_INFORMADO) & df["severidade"].notna()).sum()
    log.registrar("Severidade", corrigidas + preenchidas,
                  f"Severidade recalculada pelas contagens de vítimas: {numero_br(preenchidas)} "
                  f"'não informado' preenchidas e {numero_br(corrigidas)} contraditórias corrigidas "
                  f"(ex.: 'ileso' com feridos > 0). Ficam sem severidade "
                  f"{numero_br(df['severidade'].isna().sum())} acidentes sem nenhuma pessoa "
                  f"contabilizada.", len(df))
    df["fatal"] = df["mortos"] > 0

    # --- Veículos
    for col in config.VEICULOS:
        df[col] = bruto[col].astype(int)
    df["total_veiculos"] = df[config.VEICULOS].sum(axis=1)
    df["veiculos_informados"] = df["total_veiculos"] > 0
    sem = (~df["veiculos_informados"]).sum()
    log.registrar("Veículos", sem,
                  f"Acidentes com todas as colunas de veículo zeradas ({pct_br(sem / len(df))}"
                  f", inclusive colisões) tratados como 'veículos não informados' e "
                  f"excluídos das análises por tipo de veículo.", len(df))
    df["envolve_moto"] = (
        ((df["motocicleta"] + df["ciclomotor"]) > 0).astype("boolean")
        .where(df["veiculos_informados"])
    )
    df["perfil_veiculos"] = _perfil_veiculos(df)

    return df, log.tabela(), mapeamento_vias


def salvar(df, log, mapeamento_vias):
    config.garantir_pastas()
    df.to_parquet(config.ARQ_TRATADO, index=False)
    log.to_csv(config.ARQ_LOG_LIMPEZA, index=False)
    mapeamento_vias.to_csv(config.ARQ_VIAS_MAPEAMENTO, index=False)


def carregar():
    """Base tratada (gera a partir da bruta se ainda não existir)."""
    if not config.ARQ_TRATADO.exists():
        salvar(*tratar())
    return pd.read_parquet(config.ARQ_TRATADO)
