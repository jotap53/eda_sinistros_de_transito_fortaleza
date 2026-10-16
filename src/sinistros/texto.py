"""Normalização de texto."""

import unicodedata


def normalizar(texto):
    """Minúsculas, sem acentos e com espaços simples."""
    if texto is None or texto != texto:  # None ou NaN
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def numero_br(valor, casas=0):
    """Número no padrão brasileiro: 1.234,5."""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct_br(fracao, casas=1):
    """Fração (0 a 1) como porcentagem no padrão brasileiro: 12,3%."""
    return numero_br(100 * fracao, casas) + "%"
