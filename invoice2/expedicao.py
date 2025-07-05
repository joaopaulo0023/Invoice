import streamlit as st
import pandas as pd
from datetime import datetime, time, date
import os
from homepage import nome_usuario
from teste import EMPILHADEIRAS_VALIDAS


st.title("Check-list de Empilhadeira")

def definir_turno():
    agora = datetime.now().time()
    if time(6, 0) <= agora <= time(14, 50):
        return "1° Turno"
    elif time(15, 10) <= agora <= time(23, 20):
        return "2° Turno"
    else:
        return "3° Turno"

# Informações do operador
st.header("Informações do Operador")
turno = definir_turno()
st.header(turno)

# Campo de scanner para empilhadeira

st.markdown(
    """
    <style>
    /* Esconde o texto do input, deixando-o "invisível" */
    input[id="widget-key-scanner"] {
        color: white;
        background-color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

horimetro = col2.number_input("Horímetro Atual (horas)", min_value=0, step=1)
st.header("Scanner de Empilhadeira")
equipamento = col1.text_input(
    "Escaneie o QR Code da empilhadeira",
    value="",
    key="scanner",
    help="Use o scanner para preencher este campo",
    type="default"
)

# Injeção de JavaScript para impedir digitação manual no campo de QR Code


st.title("Check-list de Empilhadeira")

# Componente customizado para captura de QR Code
scanner_value = st.empty()  # Placeholder para exibir o valor recebido

st.markdown(
    """
    <style>
    input[aria-label="Escaneie o QR Code da empilhadeira"] {
        color: white !important;
        background-color: white !important;
        caret-color: white !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)




# Validação do QR Code
if equipamento and equipamento not in EMPILHADEIRAS_VALIDAS:
    st.error(f"Empilhadeira '{equipamento}' não cadastrada. Verifique o QR Code.")
    equipamento = None

# Verifica se o equipamento já foi registrado no dia
if equipamento and os.path.exists("checklist_empilhadeira_exp.csv"):
    df = pd.read_csv("checklist_empilhadeira_exp.csv")
    df_hoje = df[df["Data"] == str(date.today())]
    
    if equipamento in df_hoje["Identificação do Equipamento"].values:
        turno_registrado = df_hoje[df_hoje["Identificação do Equipamento"] == equipamento]["Turno"].values[0]
        st.error(f"A empilhadeira '{equipamento}' já teve seu check-list preenchido hoje no {turno_registrado}.")
        equipamento = None

# Outros dados do check-list

data = date.today()
st.write(f"Data: {data}")
registro = nome_usuario

# Só exibe o check-list se o equipamento for válido
if equipamento:
    st.header("Itens do Check-list")
    with st.expander("Preencha os itens do check-list"):
        col1, col2 = st.columns(2)

        with col1:
            checklist = {}
            checklist["Nível Agua"] = st.radio("Nível de água da bateria", ["", "Ok", "Nok"])
            checklist["Freios"] = st.radio("Óleo hidráulico e freio", ["", "Ok", "Nok"])
            checklist["Buzina"] = st.radio("Buzina", ["", "Ok", "Nok"])
            checklist["Pneus"] = st.radio("Pneus", ["", "Ok", "Nok"])
            checklist["Bateria"] = st.radio("Carga da Bateria e cabos elétricos soltos", ["", "Ok", "Nok"])
            checklist["Espelhos e retrovisores"] = st.radio("Espelhos e retrovisores", ["", "Ok", "Nok"])
            checklist["Paineis de instrumentos"] = st.radio("Paineis de instrumentos", ["", "Ok", "Nok"])
            checklist["Luzes de frente e ré"] = st.radio("Luzes de frente e ré", ["", "Ok", "Nok"])
            checklist["Alarme sonoro da marcha ré"] = st.radio("Alarme sonoro da marcha ré", ["", "Ok", "Nok"])
            checklist["Pedais de freio e acelerador"] = st.radio("Pedais de freio e acelerador", ["", "Ok", "Nok"])
            checklist["Freios de Pé e mão"] = st.radio("Freios de pé e mão", ["", "Ok", "Nok"])
        with col2:
            checklist["Controles hidráulicos, cabos e correntes"] = st.radio("Controles hidráulicos, cabos e correntes", ["", "Ok", "Nok"])
            checklist["Giroflex"] = st.radio("Giroflex", ["", "Ok", "Nok"])
            checklist["Extintor de incêndio"] = st.radio("Extintor de incêndio", ["", "Ok", "Nok"])
            checklist["Cinto de segurança"] = st.radio("Cinto de segurança", ["", "Ok", "Nok"])
            checklist["Folga na direção"] = st.radio("Folga na direção", ["", "Ok", "Nok"])
            checklist["Controle de velocidade"] = st.radio("Controle de velocidade", ["", "Ok", "Nok"])
            checklist["Garfo torre inclinação e sist rotativo"] = st.radio("Garfo, torre, inclinação e sist rotativo", ["", "Ok", "Nok"])
            checklist["Limpeza"] = st.radio("Limpeza", ["", "Ok", "Nok"])
            checklist["Avarias"] = st.radio("Avarias", ["", "Ok", "Nok"])
            checklist["Garfo prolongador"] = st.radio("Garfo prolongador", ["", "Ok", "Nok"])
            checklist["Trava de segurança da bateria"] = st.radio("Trava de segurança da bateria", ["", "Ok", "Nok"])
            checklist["Credencial"] = st.radio("Credencial", ["", "Ok", "Nok"])
            checklist["Calibragem do red zone"] = st.radio("Calibragem do red zone", ["", "Ok", "Nok"])


        # Comentários e foto
        comentarios = st.text_area("Comentários Adicionais")
        foto = st.camera_input("Tire uma foto como evidência (opcional)")

        caminho_arquivo = None
        if foto:
            diretorio_fotos = "fotos_capturadas"
            os.makedirs(diretorio_fotos, exist_ok=True)
            nome_arquivo = f"{data}_{registro}_{equipamento}.png"
            caminho_arquivo = os.path.join(diretorio_fotos, nome_arquivo)
            with open(caminho_arquivo, "wb") as arquivo:
                arquivo.write(foto.getbuffer())
            st.success(f"Foto salva com sucesso em '{caminho_arquivo}'!")
            st.image(caminho_arquivo, caption="Foto capturada")

        if st.button("Salvar Check-list"):
            if not turno or not equipamento or horimetro == 0:
                st.error("Por favor, preencha o turno, a identificação do equipamento e o horímetro.")
            elif "" in checklist.values():
                st.error("Por favor, preencha todos os itens do check-list.")
            else:
                checklist_formatado = {campo: valor for campo, valor in checklist.items()}
                checklist_formatado.update({
                    "Turno": turno,
                    "Identificação do Equipamento": equipamento,
                    "Horímetro": horimetro,
                    "Data": str(data),
                    "Registro": registro,
                    "Comentários": comentarios,
                    "Foto": caminho_arquivo if caminho_arquivo else "Não capturada"
                })
                df = pd.DataFrame([checklist_formatado])
                df.to_csv("checklist_empilhadeira_exp.csv", mode="a", header=not os.path.exists("checklist_empilhadeira_exp.csv"), index=False)
                st.success(f"Check-list do dia {data} para o equipamento '{equipamento}' foi preenchido com sucesso!")

# Exibição dos check-lists salvos
if st.checkbox("Visualizar Check-lists Salvos"):
    try:
        historico = pd.read_csv("checklist_empilhadeira_exp.csv")
        st.dataframe(historico)
    except FileNotFoundError:
        st.warning("Nenhum dado encontrado.")




