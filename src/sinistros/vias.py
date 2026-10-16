"""Padronização dos nomes de vias.

A mesma via aparece com várias grafias na base ("avenida gal osorio de paiva",
"avenida general osório de paiva", "osorio de paiva", "av gal osorio de paiva"...).
Aqui cada grafia recebe uma chave canônica, e as grafias com a mesma chave
são somadas como uma única via.

A chave é: tipo da via (rua, avenida...) + nome sem títulos (general, senador...).
Grafias sem tipo e erros de digitação são associados à via mais frequente
compatível. Todo o mapeamento fica salvo para auditoria.
"""

import difflib
import re

import pandas as pd

from .texto import normalizar

TIPOS = {
    "avenida": "avenida", "av": "avenida", "aven": "avenida", "avenids": "avenida",
    "avendia": "avenida", "aveninda": "avenida",
    "rua": "rua", "r": "rua",
    "travessa": "travessa", "tv": "travessa", "trav": "travessa",
    "alameda": "alameda", "al": "alameda",
    "estrada": "estrada", "est": "estrada",
    "praca": "praça", "pca": "praça",
    "via": "via", "viaduto": "viaduto", "ponte": "ponte", "vila": "vila",
    "rodovia": "rodovia", "rod": "rodovia", "rd": "rodovia",
}

# Abreviação -> forma por extenso. Na chave os títulos são descartados;
# no nome exibido eles aparecem por extenso.
TITULOS = {
    "gal": "general", "gen": "general", "general": "general",
    "sen": "senador", "senador": "senador",
    "prs": "presidente", "pres": "presidente", "presidente": "presidente",
    "dr": "doutor", "doutor": "doutor", "dra": "doutora", "doutora": "doutora",
    "cel": "coronel", "coronel": "coronel",
    "sgt": "sargento", "sargento": "sargento",
    "gov": "governador", "governador": "governador",
    "dep": "deputado", "deputado": "deputado",
    "duq": "duque", "duque": "duque",
    "prof": "professor", "pro": "professor", "professor": "professor", "profa": "professora",
    "professora": "professora",
    "pe": "padre", "padre": "padre",
    "eng": "engenheiro", "engenheiro": "engenheiro",
    "ten": "tenente", "tenente": "tenente",
    "cap": "capitão", "capitao": "capitão",
    "mal": "marechal", "marechal": "marechal",
    "alm": "almirante", "almirante": "almirante",
    "des": "desembargador", "desembargador": "desembargador",
    "min": "ministro", "ministro": "ministro",
    "vis": "visconde", "visconde": "visconde",
    "bar": "barão", "barao": "barão",
    "com": "comendador", "comendador": "comendador",
    "maj": "major", "major": "major",
    "brig": "brigadeiro", "brigadeiro": "brigadeiro",
    "mons": "monsenhor", "monsenhor": "monsenhor",
    "pref": "prefeito", "prefeito": "prefeito",
    "ver": "vereador", "vereador": "vereador",
    "con": "cônego", "conego": "cônego",
}

NUMERAIS = {
    "um": "1", "dois": "2", "tres": "3", "quatro": "4", "cinco": "5", "seis": "6",
    "sete": "7", "oito": "8", "nove": "9", "dez": "10", "onze": "11", "doze": "12",
    "treze": "13", "catorze": "14", "quatorze": "14", "quinze": "15",
    "dezesseis": "16", "dezessete": "17", "dezoito": "18", "dezenove": "19",
    "vinte": "20", "trinta": "30",
}

PALAVRAS_MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}

# Nomes diferentes para o mesmo corredor, confirmados pelas coordenadas: mais de
# 95% dos acidentes de um nome ficam a menos de 100-150 m dos acidentes do outro.
# A CE-040 e a BR-222 têm, dentro de Fortaleza, nome de avenida; o registro usa
# ora um, ora outro (CE-040 até 2020, Washington Soares depois).
CORREDORES = {
    "CE-040": "Av. Washington Soares / CE-040",
    "Avenida Washington Soares": "Av. Washington Soares / CE-040",
    "BR-222": "Av. Mister Hull / BR-222",
    "Avenida Mister Hull": "Av. Mister Hull / BR-222",
    "Rua Bernardo Manuel": "Avenida Bernardo Manuel",
}

RE_RODOVIA = re.compile(r"\b(br|ce)\s*-?\s*(\d{3})\b")
# Complementos depois do nome: "- oswaldo cruz", "x dom manuel", "esq.", "km 3", "n° 3290"
RE_CORTE = re.compile(
    r"(\s-|-esq\w*|\sx|\sesq|\sesquina|\ssentido|\ssentindo|\sproximo|\sprox"
    r"|\sem frente|\sn\s?[o°º]?\s*\d|\skm)(?=[\s\d]|$).*$"
)


def _limpar(nome):
    """Minúsculas, sem complementos e sem número de porta. Mantém os acentos."""
    if nome is None or nome != nome:
        return ""
    s = " ".join(str(nome).lower().split())
    s = re.sub(r"\(.*?\)", " ", s)          # "(aeroporto)", "(pici)"
    s = s.replace(".", " ").replace(",", " ")
    s = " ".join(s.split())
    s = RE_CORTE.sub("", s)
    return s.strip(" -")


def decompor(nome):
    """Devolve (tipo, núcleo, nome_exibicao) de uma grafia."""
    bruto = _limpar(nome)
    s = normalizar(bruto)
    if not s:
        return None, "", ""

    rodovia = RE_RODOVIA.search(s)
    if rodovia:
        sigla = f"{rodovia.group(1)}-{rodovia.group(2)}"
        return "rodovia", sigla, sigla.upper()

    # Número de porta no fim ("avenida santos dumont 485")
    s = re.sub(r"(\s+\d+)+$", "", s)
    tokens = s.split()
    tokens_brutos = bruto.split()[:len(tokens)]
    if len(tokens_brutos) != len(tokens):  # segurança: sem acentos então
        tokens_brutos = tokens

    tipo = TIPOS.get(tokens[0])
    if tipo:
        tokens, tokens_brutos = tokens[1:], tokens_brutos[1:]

    tokens = [NUMERAIS.get(t, t) for t in tokens]
    nucleo = " ".join(t for t in tokens if t not in TITULOS)

    exibicao_tokens = [
        TITULOS.get(t, NUMERAIS.get(t, b)) for t, b in zip(tokens, tokens_brutos)
    ]
    exibicao = " ".join(
        t if (normalizar(t) in PALAVRAS_MINUSCULAS and i > 0) else t[:1].upper() + t[1:]
        for i, t in enumerate(exibicao_tokens)
    )
    if tipo:
        exibicao = f"{tipo.capitalize()} {exibicao}".strip()
    return tipo, nucleo, exibicao


def _mesma_via_com_erro(a, b):
    """True se os núcleos diferem só por erro de digitação em palavras longas.

    Evita juntar vias de fato diferentes, como "Avenida C" e "Avenida I" de um
    conjunto, "Pedro I" e "Pedro II" ou "Isabel" e "Israel Bezerra".
    """
    ta, tb = a.split(), b.split()
    if len(ta) != len(tb):
        return False
    diferentes = [(x, y) for x, y in zip(ta, tb) if x != y]
    if not diferentes:
        return True
    return all(
        len(x) >= 4 and len(y) >= 4
        and difflib.SequenceMatcher(None, x, y).ratio() >= 0.85
        for x, y in diferentes
    )


def padronizar_vias(serie, limiar_similaridade=0.92):
    """Mapeia cada grafia de `serie` para um nome canônico de via.

    Retorna (série com o nome canônico, tabela de mapeamento para auditoria).
    """
    contagem = serie.dropna().value_counts()
    linhas = []
    for grafia, n in contagem.items():
        tipo, nucleo, exibicao = decompor(grafia)
        linhas.append({"grafia": grafia, "registros": n, "tipo": tipo,
                       "nucleo": nucleo, "exibicao": exibicao})
    m = pd.DataFrame(linhas)
    m = m[m["nucleo"] != ""]
    m["chave"] = m["tipo"].fillna("?") + "|" + m["nucleo"]
    m["regra"] = "exata"

    total_por_chave = m.groupby("chave")["registros"].sum()

    # 1) Erros de digitação: chave rara -> chave do mesmo tipo muito mais frequente
    #    e quase idêntica ("godofredo marciel" -> "godofredo maciel").
    frequentes = total_por_chave[total_por_chave >= 20].sort_values(ascending=False)
    frequentes_por_tipo = {}
    for chave, n in frequentes.items():
        tipo, nucleo = chave.split("|", 1)
        frequentes_por_tipo.setdefault(tipo, []).append((chave, nucleo, n))
    destino = {}
    for chave, n in total_por_chave.items():
        tipo, nucleo = chave.split("|", 1)
        candidatos = [(c, nc) for c, nc, nf in frequentes_por_tipo.get(tipo, [])
                      if c != chave and nf >= 5 * n]
        nucleos = [nc for _, nc in candidatos]
        for parecido in difflib.get_close_matches(nucleo, nucleos, n=3,
                                                  cutoff=limiar_similaridade):
            if _mesma_via_com_erro(nucleo, parecido):
                destino[chave] = candidatos[nucleos.index(parecido)][0]
                break
    m.loc[m["chave"].isin(destino), "regra"] = "erro de digitação"
    m["chave"] = m["chave"].replace(destino)

    # 2) Grafias sem tipo ("osorio de paiva") -> via com tipo e mesmo núcleo mais frequente
    total_por_chave = m.groupby("chave")["registros"].sum()
    com_tipo = total_por_chave[~total_por_chave.index.str.startswith("?|")]
    por_nucleo = {}
    for chave, n in com_tipo.sort_values().items():
        por_nucleo[chave.split("|", 1)[1]] = chave  # o mais frequente sobrescreve
    sem_tipo = m["chave"].str.startswith("?|")
    alvo = m.loc[sem_tipo, "chave"].str.split("|", n=1).str[1].map(por_nucleo)
    m.loc[sem_tipo & alvo.notna().reindex(m.index, fill_value=False), "regra"] = "sem tipo"
    m.loc[sem_tipo, "chave"] = alvo.fillna(m.loc[sem_tipo, "chave"])

    # Nome exibido: a forma por extenso da grafia mais frequente que tenha tipo,
    # preferindo, entre formas equivalentes, uma que tenha acentos.
    m = m.sort_values(["chave", "registros"], ascending=[True, False])
    com_tipo_exib = m[m["tipo"].notna()].drop_duplicates("chave").set_index("chave")["exibicao"]
    qualquer_exib = m.drop_duplicates("chave").set_index("chave")["exibicao"]
    exibicao = com_tipo_exib.reindex(qualquer_exib.index).fillna(qualquer_exib)
    acentuadas = {}
    for forma in m["exibicao"]:
        if " ".join(forma.lower().split()) != normalizar(forma):
            acentuadas.setdefault(normalizar(forma), forma)
    exibicao = exibicao.map(lambda f: acentuadas.get(normalizar(f), f))
    m["via"] = m["chave"].map(exibicao)

    # 3) Mesmo corredor com nomes diferentes (ver CORREDORES)
    no_corredor = m["via"].isin(CORREDORES)
    m.loc[no_corredor, "regra"] = m.loc[no_corredor, "regra"] + " + mesmo corredor"
    m["via"] = m["via"].replace(CORREDORES)

    mapa = dict(zip(m["grafia"], m["via"]))
    auditoria = (
        m[["grafia", "via", "registros", "regra"]]
        .sort_values(["via", "registros"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return serie.map(mapa), auditoria
