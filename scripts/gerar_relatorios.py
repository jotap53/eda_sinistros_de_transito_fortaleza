"""Gera os relatórios em PDF a partir de resultados/resultados.json e das figuras.

Rode o pipeline antes (notebooks/00_pipeline.ipynb ou python -m sinistros.pipeline).

Uso, a partir da raiz do projeto:
    python scripts/gerar_relatorios.py
"""

import json
import sys
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sinistros import config  # noqa: E402

# Fonte DejaVu, distribuída com o matplotlib: cobre acentos e símbolos em qualquer sistema
PASTA_FONTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", PASTA_FONTES / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", PASTA_FONTES / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

AZUL = colors.HexColor("#2a78d6")
TINTA = colors.HexColor("#0b0b0b")
TINTA_2 = colors.HexColor("#52514e")
GRADE = colors.HexColor("#e1e0d9")

E = {
    "titulo": ParagraphStyle("titulo", fontName="DejaVu-Bold", fontSize=18, leading=23,
                             textColor=TINTA, spaceAfter=4),
    "subtitulo": ParagraphStyle("subtitulo", fontName="DejaVu", fontSize=10, leading=14,
                                textColor=TINTA_2, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=13, leading=17,
                         textColor=AZUL, spaceBefore=12, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=10.5, leading=14,
                         textColor=TINTA, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="DejaVu", fontSize=9.2, leading=13.2, textColor=TINTA,
                        alignment=TA_LEFT, spaceAfter=5),
    "item": ParagraphStyle("item", fontName="DejaVu", fontSize=9.2, leading=13.2,
                           textColor=TINTA, leftIndent=12, bulletIndent=2, spaceAfter=3),
    "tab": ParagraphStyle("tab", fontName="DejaVu", fontSize=8.2, leading=10.8, textColor=TINTA),
    "tab_b": ParagraphStyle("tab_b", fontName="DejaVu-Bold", fontSize=8.2, leading=10.8,
                            textColor=colors.white),
    "nota": ParagraphStyle("nota", fontName="DejaVu", fontSize=7.8, leading=10.5,
                           textColor=TINTA_2, spaceAfter=4),
}


def n(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=1):
    return f"{n(v, casas)}%"


def P(texto, estilo="p"):
    return Paragraph(texto, E[estilo])


def itens(lista):
    return [Paragraph(t, E["item"], bulletText="•") for t in lista]


def figura(nome, largura=17, pasta=None):
    caminho = (pasta or config.FIGURAS) / f"{nome}.png"
    img = Image(str(caminho))
    proporcao = img.imageHeight / img.imageWidth
    img.drawWidth = largura * cm
    img.drawHeight = largura * cm * proporcao
    return KeepTogether([img, Spacer(1, 6)])


def tabela(linhas, larguras):
    dados = [[P(str(c), "tab_b") for c in linhas[0]]]
    dados += [[P(str(c), "tab") for c in linha] for linha in linhas[1:]]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRADE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(TINTA_2)
    canvas.drawString(2 * cm, 1.2 * cm,
                      "Sinistros de trânsito em Fortaleza, 2015-2024. Fonte: AMC / Prefeitura de "
                      "Fortaleza; IBGE, Censo 2022; OpenStreetMap.")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
    canvas.restoreState()


def documento(caminho, titulo):
    return SimpleDocTemplate(str(caminho), pagesize=A4, title=titulo,
                             leftMargin=2 * cm, rightMargin=2 * cm,
                             topMargin=1.8 * cm, bottomMargin=2 * cm)


def tabela_hipoteses(r):
    h1, h2, h3, h4, h5 = r["h1"], r["h2"], r["h3"], r["h4"], r["h5"]
    om = h1["or_ajustado"]
    return tabela([
        ["Hipótese", "Resultado", "Conclusão"],
        ["H1. A letalidade é maior de madrugada e no fim de semana",
         f"Chance de morte: madrugada {n(om['Madrugada (vs. manhã)']['or'], 2)}×, noite "
         f"{n(om['Noite (vs. manhã)']['or'], 2)}× (vs. manhã); fim de semana "
         f"{n(om['Fim de semana (vs. dia útil)']['or'], 2)}× (vs. dia útil), já descontado o "
         f"efeito dos veículos e do ano", "Confirmada: efeitos independentes"],
        ["H2. A presença de motos aumenta o número de vítimas",
         f"{pct(h2['pct_com_vitima_moto'])} dos acidentes com moto têm vítima, contra "
         f"{pct(h2['pct_com_vitima_sem_moto'])} sem moto; número de vítimas "
         f"{n(100 * (h2['irr']['Só moto']['irr'] - 1))}% maior que em acidentes só com carro",
         "Confirmada"],
        ["H3. Os acidentes caem ao longo do tempo",
         f"Degrau em jan/2018 ({n(abs(h3['degrau_mensal']))} acidentes/mês a menos), sem "
         f"tendência dentro de cada período; mortes caem {n(abs(h3['mortes_variacao_anual_pct']), 1)}% "
         f"ao ano", "Revista: mudança de patamar (provável registro); queda real nas mortes"],
        ["H4. O controle de tráfego se associa à gravidade",
         f"Associação geral fraca (V = {n(h4['v_cramer_sem_ni'], 2)}); sem controle: chance de "
         f"morte {n(h4['or']['Sem controle (vs. semáforo)']['or'], 2)}× a de semáforos",
         "Parcial: vale só para os 39% com a informação"],
        ["H5. População e malha viária explicam os acidentes por bairro",
         f"Explicam cerca de {n(100 * h5['pseudo_r2']['População + km de vias'])}% da variação; "
         f"Centro, Aldeota e Meireles têm 2,6 a 4,2 vezes o esperado",
         "Revista: explica parte; polos de comércio e passagem ficam bem acima do esperado"],
    ], [4.6, 8.4, 4])


# ===================================================================== Executivo

def relatorio_executivo(r):
    p1, p3, p4, p7, vias = r["passo1"], r["passo3"], r["passo4"], r["passo7"], r["vias"]
    h1, h3 = r["h1"], r["h3"]
    br116 = next(v for v in vias["top_mortos"] if v["via"] == "BR-116")
    corpo = [
        P("Sinistros de trânsito em Fortaleza, 2015-2024", "titulo"),
        P(f"Relatório executivo. Base: {n(p1['acidentes'])} acidentes registrados pela AMC, "
          f"com {n(p1['mortos'])} mortos.", "subtitulo"),

        P("Resumo", "h1"),
        *itens([
            f"<b>As mortes caem de forma contínua:</b> de {n(p1['mortos_2015'])} em 2015 para "
            f"{n(p1['mortos_2024'])} em 2024, cerca de {n(abs(h3['mortes_variacao_anual_pct']), 1)}% "
            f"a menos por ano.",
            "<b>A queda no número de acidentes não é uma tendência:</b> é um degrau em janeiro "
            "de 2018, provavelmente uma mudança na forma de registro, que deve ser confirmada com a AMC.",
            f"<b>A noite e o fim de semana matam mais:</b> um acidente na madrugada de fim de semana "
            f"tem {pct(p3['letalidade_fds_madrugada'], 1)} de chance de ser fatal, 3 vezes a da manhã "
            f"de dia útil ({pct(p3['letalidade_util_manha'], 2)}).",
            f"<b>Atropelamentos</b> são {pct(p7['pct_fatais_atropelamento'], 0)} dos acidentes "
            f"fatais; com moto envolvida, quase todo acidente deixa vítima.",
            f"<b>A BR-116 é a via mais letal:</b> {n(br116['mortos'])} mortes em 10 anos, quase o "
            f"dobro da segunda via. O Centro concentra acidentes mesmo considerando sua população.",
        ]),

        P("1. Quando os acidentes acontecem e quando matam", "h1"),
        P(f"Os acidentes acompanham os horários de deslocamento, com picos às 7h e às 16h. A "
          f"<b>gravidade</b> segue outro padrão: a letalidade é de {pct(p3['letalidade_madrugada'], 2)} "
          f"de madrugada contra {pct(p3['letalidade_manha'], 2)} de manhã. Considerando ao mesmo tempo "
          f"o horário, o dia, os veículos e o ano, a chance de um acidente ser fatal é "
          f"{n(h1['or_ajustado']['Madrugada (vs. manhã)']['or'], 1)} vez maior de madrugada e "
          f"{n(h1['or_ajustado']['Fim de semana (vs. dia útil)']['or'], 1)} vez maior no fim de "
          f"semana. Os dois efeitos são independentes e se somam."),
        figura("06_letalidade_faixa_fim_de_semana", 16),

        P("2. Tendência: o que de fato melhorou", "h1"),
        P(f"Até 2017 eram cerca de {n(p1['media_anual_2015_2017'] / 1000, 1)} mil acidentes por "
          f"ano; de 2018 em diante, {n(p1['media_anual_2018_2024'] / 1000, 1)} mil. A queda aconteceu "
          f"num único mês (janeiro de 2018) e não continuou depois. Uma mudança tão abrupta é típica de "
          f"mudança no registro. As mortes, menos sensíveis a isso, não têm esse degrau e caem ano a ano."),
        figura("20_h3_tendencia", 17),

        P("3. Onde: bairros e vias", "h1"),
        P(f"O Centro tem {n(p4['top_acidentes'][0]['acidentes'])} acidentes, "
          f"{n(p4['top_acidentes'][0]['por_10k_hab_ano'])} por 10 mil habitantes por ano, contra uma "
          f"média de {n(p4['media_cidade_acid_10k_hab_ano'])} na cidade. População e malha viária "
          f"explicam cerca de {n(100 * r['h5']['pseudo_r2']['População + km de vias'])}% das "
          f"diferenças entre bairros. Os bairros que mais excedem o esperado (Centro, Aldeota, "
          f"Meireles, José Bonifácio, Fátima, Parangaba) são polos de comércio e de passagem. As "
          f"mortes por habitante pesam nos bairros cortados por rodovias, como Cajazeiras (BR-116)."),
        figura("22_h5_bairros_observado_esperado", 15),
        P(f"Entre as vias, o corredor <b>Av. Washington Soares / CE-040</b> lidera em acidentes "
          f"({n(vias['top'][0]['acidentes'])}); os dois nomes são a mesma via e antes eram contados "
          f"separadamente. A <b>BR-116</b> lidera em mortes ({n(br116['mortos'])})."),
        figura("23_vias_top20", 16),

        P("4. Veículos e tipos de acidente", "h1"),
        P(f"Automóvel e moto estão na maioria dos acidentes. Os mais letais envolvem caminhão "
          f"({pct(p7['por_veiculo']['Caminhão']['pct'])}), ônibus "
          f"({pct(p7['por_veiculo']['Ônibus']['pct'])}) e bicicleta "
          f"({pct(p7['por_veiculo']['Bicicleta']['pct'])}), contra "
          f"{pct(p7['por_veiculo']['Automóvel']['pct'])} com automóvel. Por tipo de acidente, choques "
          f"com obstáculo ({pct(p7['obstaculo_pct'])}) e atropelamentos ({pct(p7['atropelamento_pct'])}) "
          f"são os mais letais."),
        figura("13_letalidade_por_veiculo", 15.5),

        P("5. As cinco hipóteses", "h1"),
        tabela_hipoteses(r),
        Spacer(1, 8),

        P("6. Recomendações", "h1"),
        *itens([
            "<b>Fiscalização</b> concentrada nas noites e madrugadas, sobretudo de sexta a domingo, "
            "e nos corredores rodoviários (BR-116, Av. Washington Soares / CE-040, Av. Osório de Paiva).",
            "<b>Proteção ao pedestre:</b> os atropelamentos respondem por mais de um terço dos "
            "acidentes fatais. Travessias seguras e redução de velocidade nos corredores.",
            "<b>Engenharia de tráfego</b> nos locais sem controle, onde a chance de morte é cerca de "
            "60% maior que em cruzamentos com semáforo.",
            "<b>Motociclistas:</b> quase todo acidente com moto deixa vítima. Campanhas e "
            "equipamentos de proteção.",
            "<b>Qualidade do registro:</b> esclarecer a mudança de janeiro de 2018 e voltar a preencher "
            "controle de tráfego e uso do solo, que faltam em mais de 80% dos registros recentes.",
        ]),

        P("Limitações", "h1"),
        P("A base cobre os acidentes <b>registrados</b>; acidentes sem vítima tendem a ser menos "
          "registrados. Não há dados de fluxo de veículos, álcool ou velocidade, então os resultados "
          "mostram <b>associações</b>, não causas. Controle de tráfego e uso do solo estão ausentes "
          "na maioria dos registros recentes.", "nota"),
    ]
    caminho = config.RELATORIOS / "relatorio_executivo.pdf"
    documento(caminho, "Relatório executivo: sinistros de trânsito em Fortaleza").build(
        corpo, onFirstPage=rodape, onLaterPages=rodape)
    return caminho


# ===================================================================== Passos

def relatorio_passos(r):
    p1, p2, p3, p4, p5 = r["passo1"], r["passo2"], r["passo3"], r["passo4"], r["passo5"]
    p6, p7, p8, p9, p10 = r["passo6"], r["passo7"], r["passo8"], r["passo9"], r["passo10"]
    h1, h2, h3, h4, h5 = r["h1"], r["h2"], r["h3"], r["h4"], r["h5"]
    log = r["limpeza"]

    def mudou(texto):
        return P(f"<b>O que mudou em relação à versão anterior:</b> {texto}", "nota")

    corpo = [
        P("Detalhamento dos passos da análise", "titulo"),
        P("Sinistros de trânsito em Fortaleza, 2015-2024: limpeza, análise exploratória e testes "
          "estatísticos, passo a passo.", "subtitulo"),
        figura("00_pipeline", 13),

        P("Preparação dos dados", "h1"),
        P(f"A base recebida tem {n(log[0]['linhas_resultantes'])} registros. Decisões de tratamento:"),
        *itens([f"<b>{x['etapa']}:</b> {x['descricao']}" for x in log[1:]]),
        P("Também foram usados dados externos por bairro: limites e população (IBGE, Censo 2022) e "
          "km de vias e cruzamentos (OpenStreetMap)."),
        figura("01_qualidade_nao_informado_por_ano", 15),

        PageBreak(),
        P("Passo 1. Visão geral", "h1"),
        P(f"{n(p1['acidentes'])} acidentes, {n(p1['mortos'])} mortos em {n(p1['acidentes_fatais'])} "
          f"acidentes fatais (letalidade de {pct(p1['letalidade_pct'], 2)}); "
          f"{pct(p1['pct_com_vitima'], 0)} dos acidentes têm vítima. Os acidentes têm dois patamares "
          f"({n(p1['media_anual_2015_2017'] / 1000, 1)} mil/ano até 2017 e "
          f"{n(p1['media_anual_2018_2024'] / 1000, 1)} mil/ano depois); as mortes caem de "
          f"{n(p1['mortos_2015'])} para {n(p1['mortos_2024'])}."),
        figura("02_acidentes_e_mortes_por_ano", 16),
        mudou("severidade recalculada pelas vítimas; 54 duplicatas removidas."),

        P("Passo 2. Horários", "h1"),
        P(f"Pico às {p2['hora_pico']}h ({n(p2['acidentes_pico'])} acidentes) e às 7h. Nos fins de "
          f"semana, as madrugadas têm 2 a 3 vezes mais acidentes por dia que nos dias úteis."),
        figura("05_mapa_calor_dia_hora", 16),

        P("Passo 3. Faixa horária e fim de semana", "h1"),
        P(f"O fim de semana tem {pct(p3['pct_fim_de_semana'])} dos acidentes, mas por dia o sábado "
          f"({n(p3['media_sabado'], 1)}) fica no nível dos dias úteis ({n(p3['media_dia_util'], 1)}); "
          f"só o domingo tem menos ({n(p3['media_domingo'], 1)}). A letalidade é maior de madrugada "
          f"({pct(p3['letalidade_madrugada'], 2)}) e na madrugada de fim de semana chega a "
          f"{pct(p3['letalidade_fds_madrugada'], 2)}."),
        mudou("intervalos de confiança; comparação por dia, não só pelo total."),

        P("Passo 4. Bairros", "h1"),
        P("Acidentes: " + "; ".join(
            f"{b['bairro']} {n(b['acidentes'])} ({pct(b['pct'])}, {n(b['por_10k_hab_ano'])} por 10 "
            f"mil hab./ano)" for b in p4["top_acidentes"][:3]) + ". Mortes por habitante (bairros "
          "com 10 mortes ou mais): " + "; ".join(
            f"{b['bairro']} {n(b['por_100k_hab_ano'], 1)}" for b in p4["top_taxa_mortos"][:4])
          + f" por 100 mil hab./ano (média da cidade: {n(p4['media_cidade_mortos_100k_hab_ano'], 1)})."),
        figura("07_bairros_total_e_taxa", 16),
        figura("09_mapa_bairros_mortes_por_habitante", 11),
        mudou("bairro oficial pelas coordenadas (IBGE 2022) e taxas por habitante."),

        P("Passo 5. Veículos envolvidos", "h1"),
        P(f"Entre os {n(p5['acidentes_com_veiculo_informado'])} acidentes com veículos informados, "
          f"automóvel aparece em {pct(p5['pct_com_automovel'])} e moto em {pct(p5['pct_com_moto'])}."),
        mudou("acidentes sem veículo informado (9%) excluídos; medida em % de acidentes, não % de "
              "veículos."),

        P("Passo 6. Co-ocorrência", "h1"),
        P(f"Carro + moto: {n(p6['auto_e_moto'])} acidentes. Só automóveis: {n(p6['so_automovel'])}; "
          f"só motos: {n(p6['so_moto'])}. Bicicleta com automóvel: {n(p6['bicicleta_e_automovel'])}; "
          f"com moto: {n(p6['bicicleta_e_moto'])}."),
        figura("12_coocorrencia_veiculos", 11),
        mudou("a versão anterior chamava de 'exclusivamente automóveis' os acidentes com automóvel "
              "e qualquer outro veículo."),

        P("Passo 7. Letalidade", "h1"),
        P("Por veículo: " + "; ".join(
            f"{k} {pct(v['pct'], 2)} (n = {n(v['n'])})" for k, v in p7["por_veiculo"].items()
            if v["n"] >= 500) + f". Atropelamento: {pct(p7['atropelamento_pct'], 2)}; choque com "
          f"obstáculo fixo: {pct(p7['obstaculo_pct'], 2)}."),
        figura("14_letalidade_por_natureza", 15),
        mudou("intervalos de confiança; ciclomotor (576 casos) sinalizado como estimativa imprecisa."),

        P("Passo 8. Correlação", "h1"),
        P(f"Spearman: moto × feridos {n(p8['moto_feridos'], 2)}; automóvel × ilesos "
          f"{n(p8['auto_ilesos'], 2)}; automóvel × total de veículos {n(p8['auto_total'], 2)} "
          f"(estrutural). Nenhuma variável se correlaciona com mortos (evento raro)."),
        mudou("Spearman no lugar de Pearson, adequado a contagens."),

        PageBreak(),
        P("Passo 9. Qui-quadrado", "h1"),
        P(f"Controle de tráfego × severidade: V de Cramér = {n(p9['controle']['v_cramer'], 3)} sem "
          f"'não informado' (era {n(p9['controle_com_ni']['v_cramer'], 2)} com ele). Tipo de "
          f"cruzamento × severidade: V = {n(p9['cruzamento']['v_cramer'], 3)}. Excluídas categorias "
          f"com menos de 100 casos: {', '.join(p9['controle']['descartadas'] + p9['cruzamento']['descartadas'])}."),
        figura("16_qui_quadrado_residuos", 16.5),
        mudou("o 'não informado' (61% da variável) era tratado como categoria e inflava a associação."),

        P("Passo 10. Vítimas por natureza e por perfil de veículos", "h1"),
        P(f"Kruskal-Wallis: natureza eta² = {n(p10['natureza']['eta2'], 3)}; perfil de veículos "
          f"eta² = {n(p10['perfil']['eta2'], 3)}."),
        mudou(f"o R² de {n(p10['r2_tautologico_feridos_severidade'], 2)} entre feridos e severidade "
              f"foi removido: é tautológico, pois a severidade é definida pelos feridos."),

        P("Passo 11. As cinco hipóteses", "h1"),
        P("H1. Letalidade, madrugada e fim de semana", "h2"),
        P(f"Regressão logística com {n(h1['n_modelo'])} acidentes. Razões de chances ajustadas: "
          + "; ".join(f"{k} {n(v['or'], 2)} ({n(v['ic'][0], 2)}-{n(v['ic'][1], 2)})"
                      for k, v in h1["or_ajustado"].items())
          + f". Interação faixa × fim de semana não significativa (p = {n(h1['menor_p_interacao'], 2)})."),
        figura("18_h1_razao_de_chances", 15.5),
        mudou("antes, 'madrugada OU fim de semana' num único grupo; agora efeitos separados e "
              "ajustados."),

        P("H2. Motos e vítimas", "h2"),
        P(f"Com moto: {pct(h2['pct_com_vitima_moto'])} dos acidentes têm vítima; sem moto: "
          f"{pct(h2['pct_com_vitima_sem_moto'])} (RR {n(h2['rr_vitima_moto'], 2)}). Poisson com erros "
          f"robustos, razão de médias vs. só automóvel: "
          + "; ".join(f"{k} {n(v['irr'], 2)}" for k, v in h2["irr"].items()) + "."),
        mudou("Poisson no lugar de ANOVA (contagens); só acidentes com veículos informados."),

        P("H3. Tendência", "h2"),
        P(f"Quebra estrutural em {h3['quebra_mes']} (Chow F = {n(h3['quebra_F'], 1)}). Modelo "
          f"segmentado com sazonalidade e erros HAC: degrau de {n(h3['degrau_mensal'])} acidentes/mês "
          f"(p &lt; 0,001), tendência antes {n(h3['tendencia_antes_mes'], 1)}/mês "
          f"(p = {n(h3['tendencia_antes_p'], 2)}), R² {n(h3['r2_segmentado'], 2)} contra "
          f"{n(h3['r2_linear'], 2)} da reta única. Mortes: {n(h3['mortes_variacao_anual_pct'], 1)}% "
          f"ao ano (IC {n(h3['mortes_ic_pct'][0], 1)}% a {n(h3['mortes_ic_pct'][1], 1)}%)."),
        mudou("a reta única sugeria queda gradual; os dados mostram um degrau, compatível com mudança "
              "de registro."),

        P("H4. Controle de tráfego", "h2"),
        P(f"Só os {n(h4['n_sem_ni'])} acidentes com controle informado. Razão de chances de morte "
          f"(ajustada por horário, dia e ano): "
          + "; ".join(f"{k} {n(v['or'], 2)} ({n(v['ic'][0], 2)}-{n(v['ic'][1], 2)})"
                      for k, v in h4["or"].items()) + "."),
        figura("21_h4_controle_trafego", 16),

        P("H5. Bairros", "h2"),
        P("Binomial Negativa com variáveis externas. Pseudo-R²: " + "; ".join(
            f"{k} {n(v, 2)}" for k, v in h5["pseudo_r2"].items())
          + f". A versão anterior (R² {n(h5['r2_circular_versao_anterior'], 2)}) usava as motos "
          f"envolvidas nos próprios acidentes do bairro, um preditor circular."),
        mudou("dados externos (IBGE e OpenStreetMap) no lugar de uma variável derivada do desfecho."),

        P("Resumo", "h1"),
        tabela_hipoteses(r),
    ]
    caminho = config.RELATORIOS / "passos_analise.pdf"
    documento(caminho, "Detalhamento dos passos da análise").build(
        corpo, onFirstPage=rodape, onLaterPages=rodape)
    return caminho


if __name__ == "__main__":
    with open(config.ARQ_RESULTADOS, encoding="utf-8") as f:
        resultados = json.load(f)
    config.garantir_pastas()
    print(relatorio_executivo(resultados))
    print(relatorio_passos(resultados))
