"""Pipeline de análise e inferência: sinistros de trânsito em Fortaleza (2015-2024).

Mesma estrutura do pipeline original: a classe TrafegoPipeline e os mesmos
seis métodos (etapa_1_ingestao ... etapa_6_verificacao_hipoteses), agora com a
limpeza incluída e as análises corrigidas. Correspondência com as quatro fases
do diagrama do projeto (figuras/00_pipeline.png):

    1. Ingestão                          -> etapa_1_ingestao
    2. Transformação e enriquecimento    -> etapa_1_ingestao (pré-processamento)
    3. Modelo analítico e visualização   -> etapas 2, 3 e 4
    4. Validação de hipóteses            -> etapas 5 e 6

Uso (a partir da raiz do projeto):
    python -m sinistros.pipeline          (com src/ no PYTHONPATH)
ou no notebook notebooks/00_pipeline.ipynb.
"""

import json
import warnings

import matplotlib
import pandas as pd

from . import analises, config, graficos, limpeza
from .externos import carregar_bairros

warnings.filterwarnings("ignore")


def _serializavel(obj):
    if isinstance(obj, dict):
        return {str(k): _serializavel(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializavel(v) for v in obj]
    if hasattr(obj, "item"):  # escalares numpy
        return obj.item()
    return obj


class TrafegoPipeline:

    def __init__(self, filepath=config.ARQ_BRUTO, gerar_graficos=True, verbose=True):
        self.filepath = filepath
        self.gerar_graficos = gerar_graficos
        self.verbose = verbose
        self.df = None
        self.log_limpeza = None
        self.resultados = {}
        if gerar_graficos:
            matplotlib.use("Agg")

    def _print(self, *args):
        if self.verbose:
            print(*args)

    def _figura(self, funcao, *args):
        if self.gerar_graficos:
            fig = funcao(*args)
            matplotlib.pyplot.close(fig)

    # ------------------------------------ Fases 1 e 2: ingestão e transformação
    def etapa_1_ingestao(self):
        """Leitura da base e dos dados externos, limpeza e enriquecimento."""
        self._print(">>> Etapa 1: Ingestão e pré-processamento")
        self.bruto = pd.read_csv(self.filepath, low_memory=False)
        self._print(f"Base bruta: {len(self.bruto):,} registros e {self.bruto.shape[1]} colunas")
        faltando = [p for p in (config.ARQ_MALHA_BAIRROS, config.ARQ_POP_BAIRROS,
                                config.ARQ_MALHA_VIARIA) if not p.exists()]
        if faltando:
            from .externos import baixar_tudo
            self._print("Dados externos ausentes; baixando (IBGE e OpenStreetMap)...")
            baixar_tudo()
        self._print("Dados externos: malha e população dos bairros (IBGE 2022), "
                    "malha viária (OpenStreetMap)")
        self._figura(graficos.fig00_pipeline)

        self.df, self.log_limpeza, mapeamento = limpeza.tratar(self.filepath)
        limpeza.salvar(self.df, self.log_limpeza, mapeamento)
        for _, linha in self.log_limpeza.iterrows():
            self._print(f"- {linha['etapa']}: {linha['linhas_afetadas']:,} linhas afetadas")
        self._print(f"Base tratada: {len(self.df):,} registros, {self.df.shape[1]} colunas "
                    f"-> {config.ARQ_TRATADO.relative_to(config.RAIZ)}")
        qualidade = analises.qualidade_por_ano(self.df)
        self._figura(graficos.fig01_qualidade, qualidade)
        return self

    # -------------------------------------- Fase 3: modelo analítico e visualização
    def etapa_2_analise_descritiva(self):
        """Passos 1 a 3: volume, evolução, severidade e horários."""
        self._print("\n>>> Etapa 2: Análise descritiva e temporal (passos 1 a 3)")
        p1 = analises.passo1_descritiva(self.df)
        p2 = analises.passo2_horarios(self.df)
        p3 = analises.passo3_faixa_fim_de_semana(self.df)
        self.resultados.update(passo1=p1["resumo"], passo2=p2["resumo"], passo3=p3["resumo"])
        r = p1["resumo"]
        self._print(f"{r['acidentes']:,} acidentes, {r['mortos']:,} mortos; "
                    f"letalidade {r['letalidade_pct']:.2f}%")
        self._print(f"Pico às {p2['resumo']['hora_pico']}h; letalidade na madrugada "
                    f"{p3['resumo']['letalidade_madrugada']:.2f}% vs. manhã "
                    f"{p3['resumo']['letalidade_manha']:.2f}%")
        for f, a in [(graficos.fig02_evolucao_anual, p1), (graficos.fig03_severidade, p1),
                     (graficos.fig04_por_hora, p2), (graficos.fig05_dia_hora, p2),
                     (graficos.fig06_letalidade_faixa_fds, p3)]:
            self._figura(f, a)
        return self

    def etapa_3_analise_espacial(self):
        """Passo 4 (bairros, com taxas por habitante) e ranking de vias."""
        self._print("\n>>> Etapa 3: Análise espacial (bairros e vias)")
        p4 = analises.passo4_bairros(self.df)
        vias = analises.ranking_vias(self.df)
        self.resultados.update(passo4=p4["resumo"], vias=vias["resumo"])
        self._print("Top 3 bairros em acidentes: " + ", ".join(
            f"{b['bairro']} ({b['acidentes']:,})" for b in p4["resumo"]["top_acidentes"][:3]))
        self._print("Top 3 vias: " + ", ".join(
            f"{v['via']} ({v['acidentes']:,})" for v in vias["resumo"]["top"][:3]))
        for f in (graficos.fig07_bairros, graficos.fig08_mapa_taxa_acidentes,
                  graficos.fig09_mapa_mortes, graficos.fig10_bairros_mortes_ic):
            self._figura(f, p4)
        self._figura(graficos.fig23_vias, vias)
        self._figura(graficos.fig24_mapa_vias, self.df, vias, carregar_bairros())
        return self

    def etapa_4_veiculos_coocorrencia(self):
        """Passos 5 a 8: veículos, co-ocorrência, letalidade e correlação."""
        self._print("\n>>> Etapa 4: Veículos, letalidade e correlação (passos 5 a 8)")
        p5 = analises.passo5_veiculos(self.df)
        p6 = analises.passo6_coocorrencia(self.df)
        p7 = analises.passo7_letalidade(self.df)
        p8 = analises.passo8_correlacao(self.df)
        self.resultados.update(passo5=p5["resumo"], passo6=p6["resumo"],
                               passo7=p7["resumo"], passo8=p8["resumo"])
        self._print(f"Automóvel + moto no mesmo acidente: {p6['resumo']['auto_e_moto']:,}")
        self._figura(graficos.fig11_veiculos, p5)
        self._figura(graficos.fig12_coocorrencia, p6)
        self._figura(graficos.fig13_letalidade_veiculo, p7)
        self._figura(graficos.fig14_letalidade_natureza, p7)
        self._figura(graficos.fig15_correlacao, p8)
        return self

    # ----------------------------------------------- Fase 4: validação de hipóteses
    def etapa_5_testes_inferenciais(self):
        """Passos 9 e 10: qui-quadrado (sem 'não informado') e Kruskal-Wallis."""
        self._print("\n>>> Etapa 5: Testes inferenciais (passos 9 e 10)")
        p9 = analises.passo9_qui_quadrado(self.df)
        p10 = analises.passo10_quanti_quali(self.df)
        self.resultados.update(passo9=p9["resumo"], passo10=p10["resumo"])
        r = p9["resumo"]
        self._print(f"Controle x severidade: V = {r['controle']['v_cramer']:.3f} "
                    f"(era {r['controle_com_ni']['v_cramer']:.3f} com 'não informado')")
        self._print(f"Cruzamento x severidade: V = {r['cruzamento']['v_cramer']:.3f}")
        self._figura(graficos.fig16_qui_quadrado, p9)
        self._figura(graficos.fig17_vitimas_natureza, p10)
        return self

    def etapa_6_verificacao_hipoteses(self):
        """Passo 11: as 5 hipóteses."""
        self._print("\n>>> Etapa 6: Validação das 5 hipóteses (passo 11)")
        h = {
            "h1": analises.h1_madrugada_fim_de_semana(self.df),
            "h2": analises.h2_motos_feridos(self.df),
            "h3": analises.h3_tendencia(self.df),
            "h4": analises.h4_controle_trafego(self.df),
            "h5": analises.h5_bairros(self.df),
        }
        self.resultados.update({k: v["resumo"] for k, v in h.items()})
        r1 = h["h1"]["resumo"]
        self._print(f"H1: na madrugada, {r1['madrugada_mortos_100_dias_fds']:.1f} mortos a cada 100 "
                    f"dias de fim de semana vs. {r1['madrugada_mortos_100_dias_util']:.1f} em dia útil "
                    f"(razão {r1['razao_mortes_dia']:.2f})")
        self._print(f"H2: com moto, {h['h2']['resumo']['pct_com_vitima_moto']:.1f}% têm vítima "
                    f"(sem moto: {h['h2']['resumo']['pct_com_vitima_sem_moto']:.1f}%)")
        r3 = h["h3"]["resumo"]
        self._print(f"H3: quebra em {r3['quebra_mes']}; mortes "
                    f"{r3['mortes_variacao_anual_pct']:.1f}% ao ano")
        or4 = h["h4"]["resumo"]["or"]["Sem controle (vs. semáforo)"]
        self._print(f"H4: sem controle vs. semáforo, OR {or4['or']:.2f}")
        self._print(f"H5: pseudo-R² {h['h5']['resumo']['pseudo_r2']['População + km de vias']:.2f} "
                    f"(versão anterior circular: {h['h5']['resumo']['r2_circular_versao_anterior']:.2f})")
        self._figura(graficos.fig18_h1, h["h1"])
        self._figura(graficos.fig19_h2, h["h2"])
        self._figura(graficos.fig20_h3, h["h3"])
        self._figura(graficos.fig21_h4, h["h4"])
        self._figura(graficos.fig22_h5, h["h5"])
        return self

    def salvar_resultados(self):
        config.garantir_pastas()
        self.resultados["limpeza"] = self.log_limpeza.to_dict(orient="records")
        with open(config.ARQ_RESULTADOS, "w", encoding="utf-8") as f:
            json.dump(_serializavel(self.resultados), f, ensure_ascii=False, indent=2)
        self._print(f"\nResultados salvos em {config.ARQ_RESULTADOS.relative_to(config.RAIZ)}")
        if self.gerar_graficos:
            self._print(f"Gráficos salvos em {config.FIGURAS.relative_to(config.RAIZ)}/")
        from .dashboard_dados import exportar
        pasta = exportar(self.df, _serializavel(self.resultados))
        self._print(f"Dados do dashboard atualizados em {pasta.relative_to(config.RAIZ)}")
        return self

    def executar(self):
        (
            self.etapa_1_ingestao()
            .etapa_2_analise_descritiva()
            .etapa_3_analise_espacial()
            .etapa_4_veiculos_coocorrencia()
            .etapa_5_testes_inferenciais()
            .etapa_6_verificacao_hipoteses()
            .salvar_resultados()
        )
        self._print("\nPipeline executado de ponta a ponta.")
        return self


if __name__ == "__main__":
    TrafegoPipeline().executar()
