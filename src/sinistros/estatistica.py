"""Ferramentas estatísticas usadas nas análises."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.contingency_tables import Table2x2
from statsmodels.stats.proportion import proportion_confint

from . import config


def proporcao_ic(sucessos, total, alpha=0.05):
    """Proporção com intervalo de confiança de Wilson (em %)."""
    sucessos, total = np.asarray(sucessos), np.asarray(total)
    inf, sup = proportion_confint(sucessos, total, alpha=alpha, method="wilson")
    return pd.DataFrame({
        "n": total, "eventos": sucessos, "pct": 100 * sucessos / total,
        "ic_inf": 100 * inf, "ic_sup": 100 * sup,
    })


def taxa_por_grupo(df, grupo, evento):
    """% de `evento` (booleano) em cada categoria de `grupo`, com IC 95%."""
    g = df.groupby(grupo, observed=True)[evento].agg(["sum", "count"])
    out = proporcao_ic(g["sum"].values, g["count"].values)
    out.index = g.index
    return out


def cramers_v(tabela):
    chi2 = stats.chi2_contingency(tabela, correction=False)[0]
    n = tabela.to_numpy().sum()
    r, k = tabela.shape
    return float(np.sqrt(chi2 / (n * (min(r, k) - 1))))


def qui_quadrado(df, linhas, colunas, excluir=(config.NAO_INFORMADO,), min_linha=100):
    """Teste qui-quadrado de independência, sem as categorias 'não informado'.

    Linhas com menos de `min_linha` casos são descartadas: elas geram
    frequências esperadas abaixo de 5, o que invalida a aproximação do teste.

    Retorna dict com estatística, p, V de Cramér, n, menor frequência
    esperada, categorias descartadas e os resíduos padronizados ajustados
    (|r| > 2 indica as células que mais se afastam da independência).
    """
    d = df[[linhas, colunas]].dropna()
    for col in (linhas, colunas):
        d = d[~d[col].astype(str).isin(excluir)]
    tab = pd.crosstab(d[linhas], d[colunas])
    tab = tab.loc[tab.sum(axis=1) > 0, tab.sum(axis=0) > 0]
    descartadas = tab.index[tab.sum(axis=1) < min_linha].astype(str).tolist()
    tab = tab[tab.sum(axis=1) >= min_linha]
    chi2, p, gl, esperado = stats.chi2_contingency(tab, correction=False)
    n = tab.to_numpy().sum()
    lin = tab.sum(axis=1).to_numpy()[:, None] / n
    col = tab.sum(axis=0).to_numpy()[None, :] / n
    residuos = (tab - esperado) / np.sqrt(esperado * (1 - lin) * (1 - col))
    return {
        "tabela": tab, "qui2": float(chi2), "p": float(p), "gl": int(gl),
        "v_cramer": cramers_v(tab), "n": int(n),
        "menor_esperado": float(esperado.min()), "descartadas": descartadas,
        "residuos": residuos,
    }


def risco_relativo(df, exposicao, evento):
    """Risco relativo e razão de chances de `evento` para `exposicao` (booleanos)."""
    d = df[[exposicao, evento]].dropna()
    a = int((d[exposicao] & d[evento]).sum())
    b = int((d[exposicao] & ~d[evento]).sum())
    c = int((~d[exposicao] & d[evento]).sum())
    e = int((~d[exposicao] & ~d[evento]).sum())
    t = Table2x2(np.array([[a, b], [c, e]]))
    rr_ic = t.riskratio_confint()
    or_ic = t.oddsratio_confint()
    return {
        "risco_exposto_pct": 100 * a / (a + b), "risco_nao_exposto_pct": 100 * c / (c + e),
        "rr": float(t.riskratio), "rr_ic": [float(rr_ic[0]), float(rr_ic[1])],
        "or": float(t.oddsratio), "or_ic": [float(or_ic[0]), float(or_ic[1])],
        "p": float(t.test_nominal_association().pvalue), "n": a + b + c + e,
    }


def tabela_coeficientes(modelo, exponenciar=True, nomes=None):
    """Coeficientes de um modelo statsmodels como tabela (exp() = OR ou IRR)."""
    ic = modelo.conf_int()
    tab = pd.DataFrame({
        "coef": modelo.params, "ic_inf": ic[0], "ic_sup": ic[1], "p": modelo.pvalues,
    }).drop(index="Intercept", errors="ignore")
    if exponenciar:
        tab[["coef", "ic_inf", "ic_sup"]] = np.exp(tab[["coef", "ic_inf", "ic_sup"]])
    if nomes:
        tab.index = [nomes.get(i, i) for i in tab.index]
    return tab


def regressao_logistica(df, formula):
    """Regressão logística (GLM binomial). Devolve o modelo ajustado.

    O desfecho é convertido para 0/1: com um booleano, o patsy criaria duas
    colunas e o modelo passaria a estimar a chance de "False".
    """
    desfecho = formula.split("~")[0].strip()
    dados = df.assign(**{desfecho: df[desfecho].astype(int)})
    return smf.glm(formula, data=dados, family=sm.families.Binomial()).fit()


def regressao_poisson(df, formula):
    """Regressão de Poisson com erros-padrão robustos (sanduíche).

    Os erros robustos mantêm a inferência válida mesmo quando a variância não
    é igual à média (sub ou sobredispersão).
    """
    return smf.glm(formula, data=df, family=sm.families.Poisson()).fit(cov_type="HC0")


def teste_chow(y, X, ponto):
    """Teste de Chow para quebra estrutural em `ponto` (índice posicional)."""
    def ssr(yy, XX):
        return sm.OLS(yy, XX).fit().ssr
    k = X.shape[1]
    s_total = ssr(y, X)
    s1, s2 = ssr(y[:ponto], X[:ponto]), ssr(y[ponto:], X[ponto:])
    n = len(y)
    f = ((s_total - (s1 + s2)) / k) / ((s1 + s2) / (n - 2 * k))
    return float(f), float(stats.f.sf(f, k, n - 2 * k))


def busca_quebra(serie, margem=12):
    """Teste de Chow em todos os meses candidatos (Quandt). Devolve tabela de F."""
    y = serie.to_numpy(dtype=float)
    t = np.arange(len(y))
    X = sm.add_constant(t)
    linhas = []
    for ponto in range(margem, len(y) - margem):
        f, p = teste_chow(y, X, ponto)
        linhas.append({"mes": serie.index[ponto], "F": f, "p": p})
    return pd.DataFrame(linhas)


def binomial_negativa(df, formula, offset=None):
    """Regressão Binomial Negativa (contagens com sobredispersão).

    O parâmetro de dispersão alpha é estimado por máxima verossimilhança e o
    GLM é reajustado com ele, para obter os IRRs com erros-padrão corretos.
    """
    off = np.log(df[offset]) if offset else None
    nb = smf.negativebinomial(formula, data=df, offset=off).fit(disp=0, maxiter=500)
    alpha = float(nb.params["alpha"])
    glm = smf.glm(formula, data=df, offset=off,
                  family=sm.families.NegativeBinomial(alpha=alpha)).fit()
    return glm, alpha


def pseudo_r2_deviance(modelo):
    """Proporção da deviance explicada (análogo ao R² para GLMs)."""
    return float(1 - modelo.deviance / modelo.null_deviance)


def eta_quadrado_kruskal(h, k, n):
    """Tamanho de efeito do Kruskal-Wallis (eta² baseado em H)."""
    return float((h - k + 1) / (n - k))
