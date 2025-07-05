import streamlit as st
from data_loader import carregar_dados1
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import locale

# Ajustar o locale para exibir meses em português (se disponível)
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    pass

# Carregar base
base = carregar_dados1()

st.title("Dashboard de Logística 📊")
col_esq, col_mid, col_dir = st.columns([1, 1, 1])

# Filtro por Descrição
descricao = col_esq.selectbox("Descrição", list(base["Descricao"].unique()))
base = base[base["Descricao"] == descricao]

# --- Filtro de data ---
hoje = datetime.now().date()
dia_selecionado = col_mid.date_input("Selecione o dia", value=hoje)
# ----------------------

# Converter datas e extrair colunas de ano, mês, dia e semana
base["data"] = pd.to_datetime(base["data"], errors="coerce")
base = base.dropna(subset=["data"])
base["Ano"]    = base["data"].dt.year
base["Mês"]    = base["data"].dt.month
base["Dia"]    = base["data"].dt.date
base["Semana"] = base["data"].dt.isocalendar().week

# Formatar data selecionada
data_formatada = dia_selecionado.strftime("%d de %B de %Y").capitalize()

# --- Gráfico comparativo Ano x Mês x Semana x Dia dentro de container ---
container = st.container(border=True)
with container:
    ano_sel    = dia_selecionado.year
    mes_sel    = dia_selecionado.month
    semana_sel = dia_selecionado.isocalendar().week

    qtd_ano    = base[base["Ano"] == ano_sel]["Quantidade"].sum()
    qtd_mes    = base[(base["Ano"] == ano_sel) & (base["Mês"] == mes_sel)]["Quantidade"].sum()
    qtd_semana = base[(base["Ano"] == ano_sel) & (base["Semana"] == semana_sel)]["Quantidade"].sum()
    qtd_dia    = base[base["Dia"] == dia_selecionado]["Quantidade"].sum()

    labels = [
        f"{ano_sel}<br>{qtd_ano}",
        f"{dia_selecionado.strftime('%B de %Y').capitalize()}<br>{qtd_mes}",
        f"Semana {semana_sel}<br>{qtd_semana}",
        f"{dia_selecionado.strftime('%d/%m/%Y')}<br>{qtd_dia}"
    ]
    categorias  = ["Ano", "Mês", "Semana", "Dia"]
    quantidades = [qtd_ano, qtd_mes, qtd_semana, qtd_dia]

    fig = go.Figure(data=[
        go.Bar(
            x=categorias,
            y=quantidades,
            text=labels,
            textposition="auto",
            marker_color="indigo",
            hoverinfo="text",
            textfont=dict(size=14)
        )
    ])
    fig.update_layout(
        title=f"Comparativo de Pallets Carregados — Ano x Mês x Semana x Dia ({data_formatada})",
        xaxis_title="Período",
        yaxis_title="Qtde Pallets",
        height=400
    )
    st.plotly_chart(fig)

# --- Continuação dos filtros e gráficos por turno ---
anos_disponiveis = sorted(base["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis)
meses_filtrados  = sorted(base[base["Ano"] == ano_selecionado]["Mês"].unique())
mes_selecionado = st.sidebar.selectbox("Mês", meses_filtrados)

base_filtrada = base[(base["Ano"] == ano_selecionado) & (base["Mês"] == mes_selecionado)]
base_turno    = base_filtrada.groupby("turno")["Quantidade"].sum().reset_index()

def get_qtd_turno(turno):
    res = base_turno[base_turno["turno"] == turno]["Quantidade"]
    return float(res.iat[0]) if not res.empty else 0.0

qtd_1 = get_qtd_turno(1.0)
qtd_2 = get_qtd_turno(2.0)
qtd_3 = get_qtd_turno(3.0)

with st.container(border=True):
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.metric("Total 1° Turno", f"{qtd_1:.0f}")
    c2.metric("Total 2° Turno", f"{qtd_2:.0f}")
    c3.metric("Total 3° Turno", f"{qtd_3:.0f}")

with st.container(border=True):
    fig_turno = go.Figure(data=[
        go.Bar(
            x=base_turno["turno"],
            y=base_turno["Quantidade"],
            text=base_turno["Quantidade"],
            textposition="auto"
        )
    ])
    fig_turno.update_layout(
        title="Total por Turno",
        xaxis_title="Turno",
        yaxis_title="Quantidade"
    )
    st.plotly_chart(fig_turno)
