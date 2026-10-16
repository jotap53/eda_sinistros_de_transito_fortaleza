"""Análises do projeto: uma função por passo da EDA e por hipótese.

Cada função recebe a base tratada e devolve um dicionário com as tabelas
(DataFrames, para exibir e plotar) e os números-chave (para o relatório).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

from . import config
from . import estatistica as est
from .externos import carregar_bairros


def _com_veiculos(df):
    return df[df["veiculos_informados"]].copy()


# ---------------------------------------------------------------- Qualidade

def qualidade_por_ano(df):
    """% de 'não informado' por ano nas variáveis com lacunas."""
    cols = {
        "controle_trafego": "Controle de tráfego",
        "uso_solo": "Uso do solo",
        "tipo_cruzamento": "Tipo de cruzamento",
        "severidade_registrada": "Severidade (como registrada)",
    }
    tab = pd.DataFrame({
        nome: (df[c] == config.NAO_INFORMADO).groupby(df["ano"]).mean() * 100
        for c, nome in cols.items()
    })
    tab["Veículos (todas as colunas zeradas)"] = (
        (~df["veiculos_informados"]).groupby(df["ano"]).mean() * 100)
    return {"tabela": tab}


# ---------------------------------------------------------------- Passo 1

def passo1_descritiva(df):
    anual = df.groupby("ano").agg(
        acidentes=("data", "size"), acidentes_fatais=("fatal", "sum"),
        mortos=("mortos", "sum"), feridos=("feridos", "sum"))
    anual["letalidade_pct"] = 100 * anual["acidentes_fatais"] / anual["acidentes"]

    sev = df["severidade"].value_counts(dropna=False)
    sev.index = sev.index.astype(object).fillna("Sem informação")
    sev = pd.DataFrame({"acidentes": sev, "pct": 100 * sev / len(df)})

    numericas = df[["mortos", "feridos", "ilesos", "vitimas", "total_veiculos"]]
    desc = numericas.describe().T[["mean", "std", "min", "50%", "max"]]
    desc.loc["total_veiculos"] = (
        df.loc[df["veiculos_informados"], "total_veiculos"]
        .describe()[["mean", "std", "min", "50%", "max"]])

    antes = anual.loc[anual.index < config.ANO_QUEBRA, "acidentes"].mean()
    depois = anual.loc[anual.index >= config.ANO_QUEBRA, "acidentes"].mean()
    return {
        "anual": anual, "severidade": sev, "descritivas": desc,
        "resumo": {
            "acidentes": int(len(df)), "mortos": int(df["mortos"].sum()),
            "acidentes_fatais": int(df["fatal"].sum()),
            "letalidade_pct": float(100 * df["fatal"].mean()),
            "pct_com_vitima": float(100 * (df["vitimas"] > 0).mean()),
            "media_anual_2015_2017": float(antes), "media_anual_2018_2024": float(depois),
            "mortos_2015": int(anual.loc[2015, "mortos"]),
            "mortos_2024": int(anual.loc[2024, "mortos"]),
        },
    }


# ---------------------------------------------------------------- Passos 2 e 3

def passo2_horarios(df):
    por_hora = df["hora"].value_counts().sort_index()
    dias_por_semana = df.groupby("dia_semana", observed=True)["data"].nunique()
    dia_hora = (
        df.groupby(["dia_semana", "hora"], observed=True).size().unstack()
        .div(dias_por_semana, axis=0))
    return {
        "por_hora": por_hora, "media_dia_hora": dia_hora,
        "resumo": {
            "hora_pico": int(por_hora.idxmax()), "acidentes_pico": int(por_hora.max()),
            "hora_vale": int(por_hora.idxmin()),
        },
    }


def passo3_faixa_fim_de_semana(df):
    faixa = df["faixa_horaria"].value_counts().reindex(config.FAIXAS)
    dias = df.groupby("dia_semana", observed=True)["data"].nunique()
    media_por_dia = df.groupby("dia_semana", observed=True).size() / dias
    let_faixa = est.taxa_por_grupo(df, "faixa_horaria", "fatal")
    let_dia = est.taxa_por_grupo(df, "dia_semana", "fatal")
    let_cruzada = est.taxa_por_grupo(df, ["fim_de_semana", "faixa_horaria"], "fatal")
    return {
        "por_faixa": faixa, "media_por_dia_semana": media_por_dia,
        "letalidade_faixa": let_faixa, "letalidade_dia": let_dia,
        "letalidade_fds_faixa": let_cruzada,
        "resumo": {
            "pct_fim_de_semana": float(100 * df["fim_de_semana"].mean()),
            "media_dia_util": float(media_por_dia.iloc[:5].mean()),
            "media_sabado": float(media_por_dia["Sábado"]),
            "media_domingo": float(media_por_dia["Domingo"]),
            "letalidade_madrugada": float(let_faixa.loc["Madrugada", "pct"]),
            "letalidade_manha": float(let_faixa.loc["Manhã", "pct"]),
            "letalidade_fds_madrugada": float(let_cruzada.loc[(True, "Madrugada"), "pct"]),
            "letalidade_util_manha": float(let_cruzada.loc[(False, "Manhã"), "pct"]),
        },
    }


# ---------------------------------------------------------------- Passo 4

def tabela_bairros(df):
    """Indicadores por bairro: contagens da base + população e malha viária."""
    bairros = carregar_bairros()
    ag = (
        df.dropna(subset=["cd_bairro"]).groupby("cd_bairro")
        .agg(acidentes=("data", "size"), acidentes_fatais=("fatal", "sum"),
             mortos=("mortos", "sum"), vitimas=("vitimas", "sum"))
    )
    b = bairros.merge(ag, left_on="CD_BAIRRO", right_index=True, how="left")
    b[["acidentes", "acidentes_fatais", "mortos", "vitimas"]] = (
        b[["acidentes", "acidentes_fatais", "mortos", "vitimas"]].fillna(0))
    anos = df["ano"].nunique()
    b["acidentes_10k_hab_ano"] = b["acidentes"] / b["populacao"] * 1e4 / anos
    b["mortos_100k_hab_ano"] = b["mortos"] / b["populacao"] * 1e5 / anos
    b["acidentes_km_via_ano"] = b["acidentes"] / b["km_vias"] / anos
    b["letalidade_pct"] = 100 * b["acidentes_fatais"] / b["acidentes"]
    # IC 95% exato (Poisson) para a taxa de mortes: bairros pequenos são instáveis
    b["mortos_100k_ic_inf"] = (stats.chi2.ppf(0.025, 2 * b["mortos"]) / 2
                               / b["populacao"] * 1e5 / anos).fillna(0)
    b["mortos_100k_ic_sup"] = (stats.chi2.ppf(0.975, 2 * (b["mortos"] + 1)) / 2
                               / b["populacao"] * 1e5 / anos)
    return b


def passo4_bairros(df):
    b = tabela_bairros(df)
    total, mortos = b["acidentes"].sum(), b["mortos"].sum()
    top_acid = b.nlargest(15, "acidentes").set_index("bairro")
    top_taxa = b.nlargest(15, "acidentes_10k_hab_ano").set_index("bairro")
    top_mortos = b.nlargest(15, "mortos").set_index("bairro")
    # Para a taxa de mortes, exige-se ao menos 10 mortes no período (estabilidade)
    top_taxa_mortos = (b[b["mortos"] >= 10].nlargest(15, "mortos_100k_hab_ano")
                       .set_index("bairro"))
    return {
        "bairros": b, "top_acidentes": top_acid, "top_taxa": top_taxa,
        "top_mortos": top_mortos, "top_taxa_mortos": top_taxa_mortos,
        "resumo": {
            "top_acidentes": [
                {"bairro": n, "acidentes": int(r.acidentes),
                 "pct": float(100 * r.acidentes / total),
                 "por_10k_hab_ano": float(r.acidentes_10k_hab_ano)}
                for n, r in top_acid.head(5).iterrows()],
            "top_mortos": [
                {"bairro": n, "mortos": int(r.mortos), "pct": float(100 * r.mortos / mortos),
                 "por_100k_hab_ano": float(r.mortos_100k_hab_ano)}
                for n, r in top_mortos.head(5).iterrows()],
            "top_taxa_mortos": [
                {"bairro": n, "mortos": int(r.mortos),
                 "por_100k_hab_ano": float(r.mortos_100k_hab_ano)}
                for n, r in top_taxa_mortos.head(5).iterrows()],
            "media_cidade_acid_10k_hab_ano": float(
                total / b["populacao"].sum() * 1e4 / df["ano"].nunique()),
            "media_cidade_mortos_100k_hab_ano": float(
                mortos / b["populacao"].sum() * 1e5 / df["ano"].nunique()),
        },
    }


# ---------------------------------------------------------------- Passos 5 e 6

def passo5_veiculos(df):
    v = _com_veiculos(df)
    presenca = (v[config.VEICULOS] > 0).sum().sort_values(ascending=False)
    pct = 100 * presenca / len(v)
    quantidade = v[config.VEICULOS].sum().reindex(presenca.index)
    perfil = v["perfil_veiculos"].value_counts()
    return {
        "presenca": pd.DataFrame({"acidentes": presenca, "pct_acidentes": pct,
                                  "veiculos": quantidade}),
        "perfil": pd.DataFrame({"acidentes": perfil, "pct": 100 * perfil / len(v)}),
        "resumo": {
            "acidentes_com_veiculo_informado": int(len(v)),
            "pct_com_automovel": float(pct["automovel"]),
            "pct_com_moto": float(pct["motocicleta"]),
            "pct_moto_ou_ciclomotor": float(100 * v["envolve_moto"].mean()),
        },
    }


def passo6_coocorrencia(df, tipos=("automovel", "motocicleta", "onibus", "bicicleta",
                                   "caminhao")):
    """Co-ocorrência entre tipos de veículo.

    Fora da diagonal: acidentes que envolvem os dois tipos. Na diagonal:
    acidentes em que esse é o ÚNICO tipo de veículo envolvido.
    """
    v = _com_veiculos(df)
    presente = v[config.VEICULOS] > 0
    tipos = list(tipos)
    mat = presente[tipos].T.astype(int) @ presente[tipos].astype(int)
    so_esse = {
        t: int((presente[t] & (presente.drop(columns=t).sum(axis=1) == 0)).sum())
        for t in tipos
    }
    for t in tipos:
        mat.loc[t, t] = so_esse[t]
    mat = mat.rename(index=config.NOMES_VEICULOS, columns=config.NOMES_VEICULOS)
    return {
        "matriz": mat,
        "resumo": {
            "auto_e_moto": int(mat.loc["Automóvel", "Motocicleta"]),
            "so_automovel": so_esse["automovel"], "so_moto": so_esse["motocicleta"],
            "bicicleta_e_automovel": int(mat.loc["Bicicleta", "Automóvel"]),
            "bicicleta_e_moto": int(mat.loc["Bicicleta", "Motocicleta"]),
        },
    }


# ---------------------------------------------------------------- Passo 7

def passo7_letalidade(df):
    v = _com_veiculos(df)
    linhas = []
    for c in config.VEICULOS:
        envolvidos = v[v[c] > 0]
        linhas.append({"veiculo": config.NOMES_VEICULOS[c], "n": len(envolvidos),
                       "eventos": int(envolvidos["fatal"].sum())})
    t = pd.DataFrame(linhas)
    t = pd.concat([t[["veiculo"]], est.proporcao_ic(t["eventos"], t["n"])], axis=1)
    t = t.set_index("veiculo").sort_values("pct", ascending=False)
    t["amostra_pequena"] = t["n"] < 1000

    perfil = est.taxa_por_grupo(v, "perfil_veiculos", "fatal")
    natureza = est.taxa_por_grupo(df[df["natureza"] != config.NAO_INFORMADO],
                                  "natureza", "fatal")
    natureza = natureza[natureza["n"] >= 500].sort_values("pct", ascending=False)
    return {
        "por_veiculo": t, "por_perfil": perfil, "por_natureza": natureza,
        "por_faixa": est.taxa_por_grupo(df, "faixa_horaria", "fatal"),
        "resumo": {
            "por_veiculo": {
                i: {"pct": float(r.pct), "ic": [float(r.ic_inf), float(r.ic_sup)],
                    "n": int(r.n)} for i, r in t.iterrows()},
            "atropelamento_pct": float(natureza.loc["Atropelamento", "pct"]),
            "atropelamento_fatais": int(natureza.loc["Atropelamento", "eventos"]),
            "pct_fatais_atropelamento": float(
                100 * natureza.loc["Atropelamento", "eventos"] / df["fatal"].sum()),
            "obstaculo_pct": float(natureza.loc["Choque c/ obstáculo fixo", "pct"]),
        },
    }


# ---------------------------------------------------------------- Passo 8

def passo8_correlacao(df):
    """Correlação de Spearman (adequada a contagens pequenas e assimétricas)."""
    v = _com_veiculos(df)
    cols = ["mortos", "feridos", "ilesos", "automovel", "motocicleta", "onibus",
            "bicicleta", "caminhao", "total_veiculos"]
    nomes = {**config.NOMES_VEICULOS, "mortos": "Mortos", "feridos": "Feridos",
             "ilesos": "Ilesos", "total_veiculos": "Total de veículos"}
    corr = v[cols].corr(method="spearman").rename(index=nomes, columns=nomes)
    return {
        "matriz": corr,
        "resumo": {
            "moto_feridos": float(corr.loc["Motocicleta", "Feridos"]),
            "auto_ilesos": float(corr.loc["Automóvel", "Ilesos"]),
            "auto_total": float(corr.loc["Automóvel", "Total de veículos"]),
            "moto_mortos": float(corr.loc["Motocicleta", "Mortos"]),
        },
    }


# ---------------------------------------------------------------- Passo 9

def passo9_qui_quadrado(df):
    controle = est.qui_quadrado(df, "controle_trafego", "severidade")
    controle_com_ni = est.qui_quadrado(df, "controle_trafego", "severidade", excluir=())
    cruzamento = est.qui_quadrado(df, "tipo_cruzamento", "severidade")
    cruzamento_com_ni = est.qui_quadrado(df, "tipo_cruzamento", "severidade", excluir=())

    ni = df["controle_trafego"] == config.NAO_INFORMADO
    perfil_ni = (pd.crosstab(ni.map({True: "Controle não informado",
                                     False: "Controle informado"}),
                             df["severidade"], normalize="index") * 100)

    # Sensibilidade: o resultado se mantém em cada período?
    por_periodo = {}
    for nome, g in df.groupby(np.where(df["ano"] < config.ANO_QUEBRA,
                                       "2015-2017", "2018-2024")):
        r = est.qui_quadrado(g, "controle_trafego", "severidade")
        por_periodo[nome] = {"v_cramer": r["v_cramer"], "n": r["n"], "p": r["p"]}

    def resumo(r):
        return {k: r[k] for k in ("qui2", "p", "gl", "v_cramer", "n", "menor_esperado",
                                  "descartadas")}

    return {
        "controle": controle, "cruzamento": cruzamento, "perfil_ni": perfil_ni,
        "resumo": {
            "controle": resumo(controle), "controle_com_ni": resumo(controle_com_ni),
            "cruzamento": resumo(cruzamento), "cruzamento_com_ni": resumo(cruzamento_com_ni),
            "controle_por_periodo": por_periodo,
            "pct_controle_informado": float(100 * (~ni).mean()),
        },
    }


# ---------------------------------------------------------------- Passo 10

def passo10_quanti_quali(df):
    """Vítimas (quantitativa) por natureza e por perfil de veículos (qualitativas).

    Usa Kruskal-Wallis (as contagens de vítimas não são normais) e eta² como
    tamanho de efeito. Também mostra por que 'feridos ~ severidade' (o R² da
    versão anterior) é tautológico: a severidade é definida pelos feridos.
    """
    def kw(d, grupo):
        grupos = [g["vitimas"].to_numpy() for _, g in d.groupby(grupo, observed=True)]
        h, p = stats.kruskal(*grupos)
        return {"H": float(h), "p": float(p), "k": len(grupos), "n": int(len(d)),
                "eta2": est.eta_quadrado_kruskal(h, len(grupos), len(d))}

    nat = df[df["natureza"] != config.NAO_INFORMADO]
    nat = nat.assign(natureza=nat["natureza"].astype(str))
    nat = nat[nat["natureza"].map(nat["natureza"].value_counts()) >= 500]
    v = _com_veiculos(df)
    medias_nat = (nat.groupby("natureza")["vitimas"].agg(["mean", "count"])
                  .sort_values("mean", ascending=False))
    medias_perfil = v.groupby("perfil_veiculos", observed=True)["vitimas"].agg(
        ["mean", "count"])
    tautologia = smf.ols("feridos ~ C(severidade_registrada)", data=df).fit().rsquared
    return {
        "medias_natureza": medias_nat, "medias_perfil": medias_perfil,
        "resumo": {
            "natureza": kw(nat, "natureza"), "perfil": kw(v, "perfil_veiculos"),
            "r2_tautologico_feridos_severidade": float(tautologia),
        },
    }


# ---------------------------------------------------------------- Hipóteses

def h1_madrugada_fim_de_semana(df):
    """H1: a chance de um acidente ser fatal é maior de madrugada e no fim de semana.

    Efeitos separados (risco relativo) e regressão logística ajustada por
    faixa horária, fim de semana, perfil de veículos e ano.
    """
    rr_madrugada = est.risco_relativo(df, "madrugada", "fatal")
    rr_fds = est.risco_relativo(df, "fim_de_semana", "fatal")

    v = _com_veiculos(df).assign(
        faixa=lambda d: d["faixa_horaria"].astype(str),
        perfil=lambda d: d["perfil_veiculos"].astype(str))
    v = v[v["perfil"] != "Outros"]  # 34 casos: estimativa instável
    modelo = est.regressao_logistica(
        v, "fatal ~ C(faixa, Treatment('Manhã')) + fim_de_semana"
           " + C(perfil, Treatment('Só automóvel')) + C(ano)")
    nomes = {
        "C(faixa, Treatment('Manhã'))[T.Madrugada]": "Madrugada (vs. manhã)",
        "C(faixa, Treatment('Manhã'))[T.Tarde]": "Tarde (vs. manhã)",
        "C(faixa, Treatment('Manhã'))[T.Noite]": "Noite (vs. manhã)",
        "fim_de_semana[T.True]": "Fim de semana (vs. dia útil)",
        "C(perfil, Treatment('Só automóvel'))[T.Só moto]": "Só moto (vs. só automóvel)",
        "C(perfil, Treatment('Só automóvel'))[T.Moto + automóvel]":
            "Moto + automóvel (vs. só automóvel)",
        "C(perfil, Treatment('Só automóvel'))[T.Envolve bicicleta]":
            "Envolve bicicleta (vs. só automóvel)",
        "C(perfil, Treatment('Só automóvel'))[T.Envolve ônibus/caminhão]":
            "Envolve ônibus/caminhão (vs. só automóvel)",
    }
    ors = est.tabela_coeficientes(modelo, nomes=nomes)
    ors = ors[~ors.index.str.startswith("C(ano)")]

    interacao = est.regressao_logistica(
        df.assign(faixa=df["faixa_horaria"].astype(str)),
        "fatal ~ C(faixa, Treatment('Manhã')) * fim_de_semana")
    p_interacao = interacao.pvalues[interacao.pvalues.index.str.contains(":")]

    def r(x):
        return {k: x[k] for k in ("risco_exposto_pct", "risco_nao_exposto_pct", "rr",
                                  "rr_ic", "or", "or_ic", "p")}

    return {
        "odds_ratios": ors, "modelo": modelo,
        "resumo": {
            "rr_madrugada": r(rr_madrugada), "rr_fim_de_semana": r(rr_fds),
            "or_ajustado": {i: {"or": float(x.coef), "ic": [float(x.ic_inf), float(x.ic_sup)],
                                "p": float(x.p)} for i, x in ors.iterrows()},
            "menor_p_interacao": float(p_interacao.min()),
            "n_modelo": int(modelo.nobs),
        },
    }


def h2_motos_feridos(df):
    """H2: acidentes com moto têm mais vítimas (feridos + mortos).

    Compara (a) a chance de haver vítima e (b) o número de vítimas por
    perfil de veículos, com regressão de Poisson (erros robustos) ajustada por ano.
    """
    v = _com_veiculos(df).assign(
        com_vitima=lambda d: d["vitimas"] > 0,
        envolve_moto=lambda d: d["envolve_moto"].astype(bool),
        perfil=lambda d: d["perfil_veiculos"].astype(str))
    rr = est.risco_relativo(v, "envolve_moto", "com_vitima")
    pct_vitima = est.taxa_por_grupo(v, "perfil_veiculos", "com_vitima")
    v = v[v["perfil"] != "Outros"]
    modelo = est.regressao_poisson(
        v, "vitimas ~ C(perfil, Treatment('Só automóvel')) + C(ano)")
    nomes = {f"C(perfil, Treatment('Só automóvel'))[T.{p}]": p
             for p in ["Só moto", "Moto + automóvel", "Envolve bicicleta",
                       "Envolve ônibus/caminhão"]}
    irr = est.tabela_coeficientes(modelo, nomes=nomes)
    irr = irr[~irr.index.str.startswith("C(ano)")]
    dispersao = float(modelo.pearson_chi2 / modelo.df_resid)
    return {
        "pct_com_vitima": pct_vitima, "irr": irr,
        "resumo": {
            "pct_com_vitima_moto": rr["risco_exposto_pct"],
            "pct_com_vitima_sem_moto": rr["risco_nao_exposto_pct"],
            "rr_vitima_moto": rr["rr"], "rr_ic": rr["rr_ic"],
            "irr": {i: {"irr": float(x.coef), "ic": [float(x.ic_inf), float(x.ic_sup)],
                        "p": float(x.p)} for i, x in irr.iterrows()},
            "dispersao_poisson": dispersao,
        },
    }


def h3_tendencia(df):
    """H3: a queda no número de acidentes é tendência contínua ou mudança de patamar?

    1) Busca de quebra estrutural (Chow em todos os meses, sem os meses de
       pandemia); 2) modelo segmentado com sazonalidade e erros HAC;
    3) tendência das mortes (Poisson), menos sensível a mudanças no registro.
    """
    mensal = df.groupby(df["data"].dt.to_period("M")).size()
    mensal.index = mensal.index.to_timestamp()
    covid = (mensal.index >= "2020-03-01") & (mensal.index <= "2020-12-01")

    busca = est.busca_quebra(mensal[~covid])
    quebra = busca.loc[busca["F"].idxmax()]

    s = pd.DataFrame({"acidentes": mensal.to_numpy(), "t": np.arange(len(mensal)),
                      "mes": mensal.index.month}, index=mensal.index)
    s["apos_quebra"] = (s.index >= f"{config.ANO_QUEBRA}-01-01").astype(int)
    s["t_apos"] = s["t"] * s["apos_quebra"]
    s["covid"] = covid.astype(int)
    linear = smf.ols("acidentes ~ t", data=s).fit()
    segmentado = smf.ols("acidentes ~ t + apos_quebra + t_apos + covid + C(mes)",
                         data=s).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    s["ajuste_linear"] = linear.fittedvalues
    s["ajuste_segmentado"] = segmentado.fittedvalues

    anual = df.groupby("ano").agg(mortos=("mortos", "sum")).reset_index()
    pm = smf.glm("mortos ~ ano", data=anual,
                 family=sm.families.Poisson()).fit()
    anual["ajuste"] = pm.fittedvalues
    irr_mortes = np.exp(pm.params["ano"])
    ic_mortes = np.exp(pm.conf_int().loc["ano"]).to_numpy()

    busca_mortes = est.busca_quebra(
        df.groupby(df["data"].dt.to_period("M"))["mortos"].sum()
        .pipe(lambda x: x.set_axis(x.index.to_timestamp()))[~covid])

    p = segmentado.pvalues
    c = segmentado.params
    return {
        "serie": s, "busca_quebra": busca, "mortes_anuais": anual,
        "resumo": {
            "quebra_mes": quebra["mes"].strftime("%Y-%m"), "quebra_F": float(quebra["F"]),
            "r2_linear": float(linear.rsquared), "r2_segmentado": float(segmentado.rsquared),
            "degrau_mensal": float(c["apos_quebra"]), "degrau_p": float(p["apos_quebra"]),
            "tendencia_antes_mes": float(c["t"]), "tendencia_antes_p": float(p["t"]),
            "tendencia_depois_mes": float(c["t"] + c["t_apos"]),
            "covid_mensal": float(c["covid"]), "covid_p": float(p["covid"]),
            "media_mensal_antes": float(s.loc[s["apos_quebra"] == 0, "acidentes"].mean()),
            "media_mensal_depois_sem_covid": float(
                s.loc[(s["apos_quebra"] == 1) & (s["covid"] == 0), "acidentes"].mean()),
            "mortes_variacao_anual_pct": float(100 * (irr_mortes - 1)),
            "mortes_ic_pct": [float(100 * (ic_mortes[0] - 1)), float(100 * (ic_mortes[1] - 1))],
            "mortes_quebra_F_max": float(busca_mortes["F"].max()),
        },
    }


def h4_controle_trafego(df):
    """H4: a severidade depende do tipo de controle de tráfego do local.

    Só com o controle informado (39% da base). Letalidade por controle e
    regressão logística ajustada por faixa horária, fim de semana e ano.
    """
    d = df[df["controle_trafego"].isin(["Semáforo", "Pare", "Sem controle"])].copy()
    d["controle"] = d["controle_trafego"].astype(str)
    d["faixa"] = d["faixa_horaria"].astype(str)
    letalidade = est.taxa_por_grupo(
        df[df["controle_trafego"] != config.NAO_INFORMADO], "controle_trafego", "fatal")
    letalidade = letalidade[letalidade["n"] >= 300]
    modelo = est.regressao_logistica(
        d, "fatal ~ C(controle, Treatment('Semáforo')) + C(faixa, Treatment('Manhã'))"
           " + fim_de_semana + C(ano)")
    nomes = {
        "C(controle, Treatment('Semáforo'))[T.Pare]": "Pare (vs. semáforo)",
        "C(controle, Treatment('Semáforo'))[T.Sem controle]": "Sem controle (vs. semáforo)",
    }
    ors = est.tabela_coeficientes(modelo, nomes=nomes).loc[list(nomes.values())]

    qui = est.qui_quadrado(df, "controle_trafego", "severidade")
    qui_ni = est.qui_quadrado(df, "controle_trafego", "severidade", excluir=())
    return {
        "letalidade": letalidade, "odds_ratios": ors,
        "resumo": {
            "v_cramer_sem_ni": qui["v_cramer"], "v_cramer_com_ni": qui_ni["v_cramer"],
            "p_sem_ni": qui["p"], "n_sem_ni": qui["n"],
            "or": {i: {"or": float(x.coef), "ic": [float(x.ic_inf), float(x.ic_sup)],
                       "p": float(x.p)} for i, x in ors.iterrows()},
            "letalidade": {i: float(x.pct) for i, x in letalidade.iterrows()},
        },
    }


def h5_bairros(df):
    """H5: o volume de acidentes por bairro é explicado pela exposição.

    Binomial Negativa com variáveis EXTERNAS à base (população do Censo 2022 e
    malha viária do OpenStreetMap). A versão anterior usava a soma de motos
    envolvidas nos próprios acidentes, o que é circular.
    """
    b = tabela_bairros(df).copy()
    b["log_populacao"] = np.log(b["populacao"])
    b["log_km_vias"] = np.log(b["km_vias"])
    b["log_dens_cruzamentos"] = np.log(b["cruzamentos"] / b["km_vias"])

    modelos = {
        "População": "acidentes ~ log_populacao",
        "Km de vias": "acidentes ~ log_km_vias",
        "População + km de vias": "acidentes ~ log_populacao + log_km_vias",
        "População + km de vias + cruzamentos/km":
            "acidentes ~ log_populacao + log_km_vias + log_dens_cruzamentos",
    }
    comparacao, ajustados = [], {}
    for nome, formula in modelos.items():
        m, alpha = est.binomial_negativa(b, formula)
        ajustados[nome] = m
        comparacao.append({"modelo": nome, "pseudo_r2": est.pseudo_r2_deviance(m),
                           "aic": float(m.aic), "alpha": alpha})
    comparacao = pd.DataFrame(comparacao).set_index("modelo")

    final = ajustados["População + km de vias + cruzamentos/km"]
    coefs = est.tabela_coeficientes(final, exponenciar=False, nomes={
        "log_populacao": "log(população)", "log_km_vias": "log(km de vias)",
        "log_dens_cruzamentos": "log(cruzamentos por km)"})

    escolhido = ajustados["População + km de vias"]
    b["esperado"] = escolhido.fittedvalues
    b["razao_obs_esp"] = b["acidentes"] / b["esperado"]

    # Reprodução da versão anterior, para comparação
    agg = df.dropna(subset=["cd_bairro"]).groupby("cd_bairro")["motocicleta"].sum()
    b["motos_nos_acidentes"] = b["CD_BAIRRO"].map(agg).fillna(0)
    r2_circular = float(smf.ols("acidentes ~ motos_nos_acidentes", data=b).fit().rsquared)

    return {
        "bairros": b, "comparacao": comparacao, "coeficientes": coefs,
        "resumo": {
            "pseudo_r2": {i: float(x.pseudo_r2) for i, x in comparacao.iterrows()},
            "r2_circular_versao_anterior": r2_circular,
            "coeficientes": {i: {"coef": float(x.coef), "p": float(x.p)}
                             for i, x in coefs.iterrows()},
            "maior_excesso": [
                {"bairro": r.bairro, "observado": int(r.acidentes),
                 "esperado": float(r.esperado), "razao": float(r.razao_obs_esp)}
                for r in b.nlargest(6, "razao_obs_esp").itertuples()],
        },
    }


# ---------------------------------------------------------------- Vias

def ranking_vias(df, n=20):
    d = df.dropna(subset=["via"])
    g = d.groupby("via").agg(
        acidentes=("data", "size"), acidentes_fatais=("fatal", "sum"),
        mortos=("mortos", "sum"), latitude=("latitude", "median"),
        longitude=("longitude", "median"))
    g["letalidade_pct"] = 100 * g["acidentes_fatais"] / g["acidentes"]
    g["pct_total"] = 100 * g["acidentes"] / len(df)
    g = g.sort_values("acidentes", ascending=False)
    top = g.head(n)
    return {
        "ranking": g, "top": top,
        "resumo": {
            "vias_distintas": int(len(g)),
            "pct_top": float(top["acidentes"].sum() / len(df) * 100),
            "top": [{"via": i, "acidentes": int(r.acidentes), "mortos": int(r.mortos)}
                    for i, r in top.head(10).iterrows()],
            "top_mortos": [{"via": i, "mortos": int(r.mortos), "acidentes": int(r.acidentes)}
                           for i, r in g.nlargest(5, "mortos").iterrows()],
        },
    }
