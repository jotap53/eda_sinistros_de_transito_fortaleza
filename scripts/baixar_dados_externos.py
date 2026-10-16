"""Baixa os dados externos por bairro (IBGE Censo 2022 e OpenStreetMap).

Uso, a partir da raiz do projeto:
    python scripts/baixar_dados_externos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sinistros.externos import baixar_tudo  # noqa: E402

if __name__ == "__main__":
    baixar_tudo()
