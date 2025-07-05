# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import locale
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, time, timedelta
from data_loader import carregar_dados1
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
#from teste import EMPILHADEIRAS_VALIDAS
import os

st.header("Logistica")

# Inicializa flag de exibição do alerta
if 'show_alert' not in st.session_state:
    st.session_state['show_alert'] = True

# Sessão e usuário
secao_usuario = st.session_state
nome_usuario = secao_usuario.get("username", None)

# Layout inicial
col_esquerda, col_direita = st.columns([1, 1.5])
col_esquerda.title("Expedição")

if nome_usuario:
    nome_limpo = nome_usuario.split("@")[0]  # remove o domínio do e-mail
    col_esquerda.write(f"Bem-vindo, {nome_limpo}")


# Botões de navegação
if col_esquerda.button("Invoice"):
    st.switch_page("invoices.py")
if col_esquerda.button("Fazer check-List"):
    st.switch_page("expedicao.py")

# Determina o turno atual baseado no horário

def get_turno_atual():
    agora = datetime.now().time()
    if time(6, 0) <= agora < time(15, 10):
        return 1
    elif time(15, 10) <= agora < time(23, 10):
        return 2
    else:
        return 3    

# --- Dashboard de Logística ---
# Carrega dados e pré-processa
base = carregar_dados1()
base['data'] = pd.to_datetime(base['data'], errors='coerce')

# Filtros no sidebar: Descrição
descricao = st.sidebar.selectbox("Descrição", base["Descricao"].unique())
base_filtrada = base[base["Descricao"] == descricao]

# Agrupa dados por mês e turno
agg = (
    base_filtrada
    .groupby([base_filtrada['data'].dt.to_period("M"), 'turno'])
    .sum(numeric_only=True)
    .reset_index()
)
agg['data'] = agg['data'].dt.to_timestamp()
agg['Ano'] = agg['data'].dt.year
agg['Mês'] = agg['data'].dt.month

# Filtros no sidebar: Ano e Mês
anos_disponiveis = sorted(agg['Ano'].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis)
meses_disponiveis = sorted(agg[agg['Ano'] == ano_selecionado]['Mês'].unique())
mes_selecionado = st.sidebar.selectbox("Mês", meses_disponiveis)

# Tabela filtrada por ano e mês
tabela = agg[(agg['Ano'] == ano_selecionado) & (agg['Mês'] == mes_selecionado)]

# Totais por turno
tot1 = tabela.loc[tabela.turno == 1, "Quantidade"].sum()
tot2 = tabela.loc[tabela.turno == 2, "Quantidade"].sum()
tot3 = tabela.loc[tabela.turno == 3, "Quantidade"].sum()

# Gráficos lado a lado
col1, col2 = st.columns(2)

with col1:
    st.subheader(f"Total mensal de {descricao} - {mes_selecionado}/{ano_selecionado}")
    fig_bar = px.bar(
        agg[agg['Ano'] == ano_selecionado],
        x='data', y='Quantidade',
        labels={'data': 'Data', 'Quantidade': 'Quantidade'},
        title=f"Total Mensal de Pallets Carregados ({ano_selecionado})"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("Carregamento por Turno")
    m1, m2, m3 = st.columns(3)
    m1.metric("1° Turno", f"{tot1:.0f}")
    m2.metric("2° Turno", f"{tot2:.0f}")
    m3.metric("3° Turno", f"{tot3:.0f}")
    


# --- Dicionário mapeando os nomes dos colaboradores para os caminhos das imagens ---
COLABORADORES_FOTOS = {
    "Wilber": "imagens/wilber.png",
    "Alexandre": "imagens/alexandre.png",
    "William": "imagens/william.png",
    "Humberto": "imagens/humberto.png",
    "Cleber": "imagens/cleber.png",
    "Roberval": "imagens/roberval.png",
    "Eduardo": "imagens/eduardo.png",
    "Willian_Martins": "imagens/willian_martins.png",
    "João Paulo": "imagens/joao_paulo.jpg",
    "Luiz": "imagens/luiz.png",
    "Willian_Moraes": "imagens/willian_moraes.png",
    "André Matos": "imagens/andre_matos.png",
    "Juliana": "imagens/juliana.png",
    "Alexandre Camargo": "imagens/alexandre_camargo.png",
    "Andrews Pestana": "imagens/andrews_pestana.png",
    "André Oliveira": "imagens/andre_oliveira.png",
    "Douglas Pereira": "imagens/douglas_pereira.png",
    "Neuber Santos": "imagens/neuber_santos.png",
    "Anderson Silva": "imagens/anderson_silva.png",
    "Fernando Fernandes": "imagens/fernando_fernandes.png",
    "Rodrigo Lima": "imagens/rodrigo_lima.png",
    "Almir Santos": "imagens/almir_santos.png",
    "Marcio Marcelino": "imagens/marcio_marcelino.png"
}

# --- Conexão com o banco de dados ---
conn = sqlite3.connect('escalas.db')
c = conn.cursor()

# --- Criação da tabela ---
def setup_database():
    c.execute('''
        CREATE TABLE IF NOT EXISTS escalas (
            data TEXT,
            turno TEXT,
            trem TEXT,
            separacao TEXT,
            guarda TEXT,
            corredor TEXT,  
            carregamento TEXT,
            gate TEXT,
            toyota_psa_nissan TEXT,
            separacao_1 TEXT,
            faturamento TEXT,
            lider TEXT,
            PRIMARY KEY (data, turno)
        )
    ''')
    conn.commit()

setup_database()

# --- Configurações de Turnos e Operadores ---
OPERATORS = [
    "Wilber", "Alexandre", "William", "Humberto", "Cleber", "Roberval",
    "Eduardo", "Willian_Martins", "João Paulo", "Luiz", "Willian_Moraes"
]

# Escala fixa para os turnos definidos
FIXED_OPERATORS = {
    "1º_turno": {
        "Lider": "André Matos",
        "Auxiliar": "Juliana",
        "Operador_1": "Alexandre Camargo",
        "Operador_2": "Andrews Pestana",
        "Operador_3": "André Oliveira",
        "Operador_4": "Douglas Pereira",
        "Operador_5": "Neuber Santos",
        "Operador_6": "Anderson Silva",
        "Auxiliar_2": "Fernando Fernandes"
    },
    "2º_turno": {
        "Lider": "João Paulo",
        "Separacao_1": "Eduardo",
        # Pool comum para Trem, Separação, Guarda e Carregamento
        "Trem": ["Alexandre", "Wilber", "Luiz", "Willian_Moraes", "Humberto"],
        "Separacao": ["Alexandre", "Wilber", "Luiz", "Willian_Moraes", "Humberto"],
        "Guarda": ["Alexandre", "Wilber", "Luiz", "Willian_Moraes", "Humberto"],
        "Corredor": ["Alexandre", "Wilber", "Luiz", "Willian_Moraes", "Humberto"],
        "Carregamento": ["Alexandre", "Wilber", "Luiz", "Willian_Moraes", "Humberto"],
        # Pool único para Gate e Toyota, PSA, garantindo que sejam diferentes
        "Gate_Toyota": ["Cleber", "Roberval"],
        "Faturamento": "Willian_Martins"
    },
    "3º_turno": {
        "Lider": "Rodrigo Lima",
        "Trem": "Almir Santos",
        "Faturamento": "Marcio Marcelino"
    }
}

# Horários dos turnos
SHIFT_TIMES = {
    "1º_turno": "06:00 - 15:10",
    "2º_turno": "15:10 - 23:10",
    "3º_turno": "23:10 - 06:00"
}

# --- Forçar locale para português ---
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    st.warning("Locale pt_BR.UTF-8 não disponível. Usando tradução manual.")

# Tradução manual de dias da semana e meses
DAYS_TRANSLATION = {
    'Monday': 'segunda-feira', 'Tuesday': 'terça-feira', 'Wednesday': 'quarta-feira',
    'Thursday': 'quinta-feira', 'Friday': 'sexta-feira', 'Saturday': 'sábado', 'Sunday': 'domingo'
}
MONTHS_TRANSLATION = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}

# Se o arquivo de check-list existir, verifica empilhadeiras pendentes para hoje
if os.path.exists("checklist_empilhadeira_exp.csv"):
    df = pd.read_csv("checklist_empilhadeira_exp.csv")
    df_hoje = df[df["Data"] == str(date.today())]
    emp_realizadas = df_hoje["Identificação do Equipamento"].unique().tolist()
    emp_pendentes = [e for e in EMPILHADEIRAS_VALIDAS if e not in emp_realizadas]
    if emp_pendentes:
        popup_html = f"""
        <html>
        <head>
            <style>
                .modal-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.7);
                    z-index: 9998;
                }}
                .modal {{
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #f9f9f9;
                    color: #000;
                    padding: 20px;
                    border: 2px solid #f44336;
                    border-radius: 8px;
                    z-index: 9999;
                    max-width: 80%;
                    font-family: Arial, sans-serif;
                }}
                .modal-header {{
                    font-size: 1.5em;
                    margin-bottom: 10px;
                }}
                .modal-close {{
                    float: right;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 1.2em;
                }}
                ul {{
                    list-style: none;
                    padding-left: 0;
                }}
                li::before {{
                    content: "• ";
                    color: #f44336;
                }}
            </style>
            <script>
                function openModal() {{
                    document.getElementById("modal").style.display = "block";
                    document.getElementById("overlay").style.display = "block";
                }}
                function closeModal() {{
                    document.getElementById("modal").style.display = "none";
                    document.getElementById("overlay").style.display = "none";
                }}
                // Abre o modal imediatamente e reabre a cada 10 minutos
                window.onload = function() {{
                    openModal();
                    setInterval(openModal, 600000);
                }};
            </script>
        </head>
        <body>
            <div id="overlay" class="modal-overlay"></div>
            <div id="modal" class="modal">
                <div class="modal-header">
                    Atenção! <span class="modal-close" onclick="closeModal()">X</span>
                </div>
                <div class="modal-body">
                    As seguintes empilhadeiras ainda não realizaram o check-list hoje:
                    <ul>
                        {''.join([f"<li>{emp}</li>" for emp in emp_pendentes])}
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        components.html(popup_html, height=400)

# --- Seleção de turno e data ---
turno_selecionado = st.sidebar.selectbox("Selecione o turno", ["1º_turno", "2º_turno", "3º_turno"])
selected_date = st.sidebar.date_input("Selecione a data", value=date.today())

# Data formatada manualmente
day_of_week = DAYS_TRANSLATION.get(selected_date.strftime('%A'), selected_date.strftime('%A'))
month = MONTHS_TRANSLATION[selected_date.month]
formatted_date = f"{day_of_week}, {selected_date.day} de {month} de {selected_date.year}"




# --- Exibir escala para a data e turno selecionados ---
c.execute('''
    SELECT trem, corredor, separacao, guarda, carregamento, gate, toyota_psa_nissan, separacao_1, faturamento, lider
    FROM escalas
    WHERE data = ? AND turno = ?
''', (selected_date.isoformat(), turno_selecionado))
row = c.fetchone()

with col_direita:
    if row:
        roles = ["TREM", "SEPARAÇÃO","CORREDOR", "GUARDA", "CARREGAMENTO", "GATE",
                "TOYOTA, PSA E NISSAN", "SEPARAÇÃO 1", "FATURAMENTO", "LÍDER"]
        schedule = [(role, operator) for role, operator in zip(roles, row) if operator]
        
        # Apresentação dinâmica com auto-refresh a cada 3 segundos
        count = st_autorefresh(interval=3000, limit=1000, key="slideshow")
        index = count % len(schedule)
        current_role, current_operator = schedule[index]
        
        st.write(f"### {current_role}")
        foto_caminho = COLABORADORES_FOTOS.get(current_operator)
        if foto_caminho:
            st.image(foto_caminho, width=300)
        st.write(f"**{current_operator}**")
    else:
        st.warning("Nenhuma escala encontrada para esta data e turno.")
    

# --- Função para rotação dos operadores ---
def rotate_operators(operators):
    return operators[1:] + operators[:1]

# --- Gerar escala anual com atribuição diferenciada para cada papel ---
def generate_schedule(year):
    st.info("🔄 Gerando escala...")

    # Pool comum para Trem, Separação, Guarda e Carregamento
    common_pool = FIXED_OPERATORS["2º_turno"]["Trem"].copy()
    
    # Pool combinado para os papéis de Gate e Toyota, PSA, garantindo operadores diferentes
    gate_toyota_pool = FIXED_OPERATORS["2º_turno"]["Gate_Toyota"].copy()
    
    for day in range(1, 366):
        data = date(year, 1, 1) + timedelta(days=day - 1)
        
        # Para os papéis do pool comum, atribui operadores diferentes em cada índice
        if len(common_pool) >= 5:
            trem_operator = common_pool[0]
            separacao_operator = common_pool[1]
            guarda_operator = common_pool[2]
            carregamento_operator = common_pool[3]
            corredor_operator = common_pool[4]  # Agora temos o operador para o papel de "Corredor"
        else:
            trem_operator = common_pool[0]
            separacao_operator = common_pool[0]
            guarda_operator = common_pool[0]
            carregamento_operator = common_pool[0]
            corredor_operator = common_pool[0]
        
        # Para Gate e Toyota, PSA, use o mesmo pool garantindo colaboradores distintos:
        gate_operator = gate_toyota_pool[0]
        if len(gate_toyota_pool) > 1:
            toyota_operator = gate_toyota_pool[1]
        else:
            toyota_operator = gate_toyota_pool[0]
        
        c.execute('''
            INSERT OR REPLACE INTO escalas 
            (data, turno, trem, corredor, separacao, guarda, carregamento, gate, toyota_psa_nissan, separacao_1, faturamento, lider) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.isoformat(), "2º_turno",
            trem_operator, corredor_operator, separacao_operator, guarda_operator, carregamento_operator,
            gate_operator, toyota_operator,
            FIXED_OPERATORS["2º_turno"]["Separacao_1"],
            FIXED_OPERATORS["2º_turno"]["Faturamento"],
            FIXED_OPERATORS["2º_turno"]["Lider"]
        ))
        
        # Rotaciona os pools para o próximo dia
        common_pool = rotate_operators(common_pool)
        gate_toyota_pool = rotate_operators(gate_toyota_pool)
        
    conn.commit()
    st.success("✅ Escala gerada com sucesso!")    


conn.commit()
conn.close()
