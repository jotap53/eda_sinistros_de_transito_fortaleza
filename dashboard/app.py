"""Dashboard: sinistros de trânsito em Fortaleza (2015-2024).

Rodar localmente, a partir da raiz do projeto:
    streamlit run dashboard/app.py
"""

from pathlib import Path

import streamlit as st

from comum import estilo

st.set_page_config(page_title="Sinistros de trânsito · Fortaleza", page_icon=":material/traffic:",
                   layout="wide", initial_sidebar_state="collapsed")
estilo()
st.logo(str(Path(__file__).parent / "imagens" / "logos.png"), size="large")

paginas = [
    st.Page("paginas/visao_geral.py", title="Visão geral", icon=":material/dashboard:",
            default=True),
    st.Page("paginas/quando.py", title="Quando", icon=":material/schedule:"),
    st.Page("paginas/mapa.py", title="Mapa", icon=":material/map:"),
    st.Page("paginas/bairros_vias.py", title="Bairros e vias", icon=":material/location_city:"),
    st.Page("paginas/veiculos.py", title="Veículos", icon=":material/two_wheeler:"),
    st.Page("paginas/hipoteses.py", title="Hipóteses", icon=":material/science:"),
]
st.navigation(paginas, position="top").run()
