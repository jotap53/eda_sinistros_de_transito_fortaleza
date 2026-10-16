"""Caminhos e constantes do projeto."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

DADOS = RAIZ / "dados"
BRUTOS = DADOS / "brutos"
EXTERNOS = DADOS / "externos"
PROCESSADOS = DADOS / "processados"
FIGURAS = RAIZ / "figuras"
MAPAS = FIGURAS / "mapas"
RESULTADOS = RAIZ / "resultados"
RELATORIOS = RAIZ / "relatorios"

ARQ_BRUTO = BRUTOS / "sinistro_transito_final.csv"
ARQ_TRATADO = PROCESSADOS / "sinistros_tratados.parquet"
ARQ_LOG_LIMPEZA = PROCESSADOS / "log_limpeza.csv"
ARQ_BAIRROS = PROCESSADOS / "bairros_indicadores.csv"
ARQ_VIAS_RANKING = PROCESSADOS / "vias_ranking.csv"
ARQ_VIAS_MAPEAMENTO = PROCESSADOS / "vias_mapeamento_nomes.csv"
ARQ_RESULTADOS = RESULTADOS / "resultados.json"

# Dados externos
ARQ_MALHA_BAIRROS = EXTERNOS / "fortaleza_bairros_ibge_2022.gpkg"
ARQ_POP_BAIRROS = EXTERNOS / "fortaleza_populacao_bairros_ibge_2022.csv"
ARQ_MALHA_VIARIA = EXTERNOS / "fortaleza_malha_viaria_osm_por_bairro.csv"

URL_MALHA_BAIRROS_CE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/"
    "gpkg/UF/CE/CE_bairros_CD2022.gpkg"
)
URL_POP_BAIRROS_BR = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/"
    "Agregados_por_bairros_basico_BR_20260520.zip"
)
COD_IBGE_FORTALEZA = "2304400"

# Base de sinistros
VEICULOS = [
    "automovel", "motocicleta", "onibus", "bicicleta", "caminhao",
    "microonibus", "ciclomotor", "trem", "tracaoanimal",
]
NOMES_VEICULOS = {
    "automovel": "Automóvel", "motocicleta": "Motocicleta", "onibus": "Ônibus",
    "bicicleta": "Bicicleta", "caminhao": "Caminhão", "microonibus": "Micro-ônibus",
    "ciclomotor": "Ciclomotor", "trem": "Trem", "tracaoanimal": "Tração animal",
}
FAIXAS = ["Madrugada", "Manhã", "Tarde", "Noite"]
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
NAO_INFORMADO = "Não informado"

# Ano em que a série muda de patamar. O notebook 03 confirma a data da quebra
# com um teste de Chow em todos os meses candidatos.
ANO_QUEBRA = 2018


def garantir_pastas():
    for p in (BRUTOS, EXTERNOS, PROCESSADOS, FIGURAS, MAPAS, RESULTADOS, RELATORIOS):
        p.mkdir(parents=True, exist_ok=True)
