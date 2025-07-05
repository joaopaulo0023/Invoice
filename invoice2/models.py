import streamlit as st
from sqlalchemy import create_engine, Integer, String, Boolean, Column
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import pandas as pd
from math import ceil
from sqlalchemy import create_engine
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

db = create_engine("sqlite:///database/meubanco.db")
Session = sessionmaker(bind=db)
session = Session()

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column("id", Integer, primary_key=True, autoincrement=True)
    nome = Column("nome", String)
    senha = Column("senha", String)
    email = Column("email", String)
    admin = Column("admin", Boolean)

    def __init__(self, nome, senha, email, admin=False):
        self.nome = nome
        self.senha = senha
        self.email = email
        self.admin = admin


Base.metadata.create_all(bind=db)


# --- Configurações do Banco de Dados --- 
# db = create_engine("sqlite:///database/meubanco.db")
DATABASE_URI = r'sqlite:///C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2/meubanco1.db'
TABLE_NAME = 'dados'

# --- Outras Configurações ---
SAVE_PATH = r'C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2\Invoices'

# Inicializa a sessão para armazenar dados temporários
if 'linhas' not in st.session_state:
    st.session_state.linhas = []  
if 'paletes_quebrados' not in st.session_state:
    st.session_state.paletes_quebrados = []  
if 'id_counter' not in st.session_state:
    st.session_state.id_counter = 1

def format_num(value):
    try:
        num = float(value)
        if num == int(num):
            return str(int(num))
        else:
            return f"{num:.2f}"
    except Exception:
        return str(value)

def incluir_data(referencia, quantidade):
    try:
        if not referencia or quantidade <= 0:
            return "Dados inválidos!"

        engine = create_engine(DATABASE_URI)
        df = pd.read_sql_table(TABLE_NAME, engine)

        HEADER = [
            'referencia', 'DESCRICAO', 'quantidade', 'QTD PCS CAIXA', 'QTD CAIXAS', 'QTD CAMADAS',
            'Peso Caixa com peça', 'Peso Pallet madeira', 'Peso da Tampa', 'Peso da cantoneira',
            'Peso Stretch + Fita Arquear', 'P. BRUTO', 'Peso Caixa VAZIA', 'Peso Liq CAIXA',
            'P. LÍQUIDO',  
            'COMPR. (CM)', 'LARGURA (CM)', 'ALT. PALLET (CM)', 'ALT. CAIXA (CM)', 'ALTURA (CM)'
        ]
        df.columns = HEADER

        row_data = df[df['referencia'] == referencia].drop_duplicates(subset=['referencia'])
        if row_data.empty:
            return "Referência não encontrada!"

        results = []                  
        paletes_quebrados_result = [] 
        caixas_restantes = 0          

        for _, row in row_data.iterrows():
            # Converte os valores numéricos para float
            qtd_por_palete = float(row['quantidade'])
            qtd_pcs_caixa = float(row['QTD PCS CAIXA'])
            qtd_caixas = float(row['QTD CAIXAS'])
            
            num_paletes = quantidade // qtd_por_palete  # divisão inteira
            resto = quantidade % qtd_por_palete
            # Valores para o cálculo do peso bruto (conforme já ajustado anteriormente)
            # Para cada palete completo, cria o registro com peso total
            for _ in range(int(num_paletes)):
    
                peso_caixa_com_peca = float(row['Peso Caixa com peça'])
                qtd_caixas_valor = float(row['QTD CAIXAS'])
                peso_pallet_madeira = float(row['Peso Pallet madeira'])
                peso_tampa = float(row['Peso da Tampa'])
                peso_cantoneira = float(row['Peso da cantoneira'])
                peso_strech = float(row['Peso Stretch + Fita Arquear'])
                
                peso_bruto_calculado = (peso_caixa_com_peca * qtd_caixas_valor) \
                                    + peso_pallet_madeira + peso_tampa \
                                    + peso_cantoneira + peso_strech

                # Novo cálculo do peso líquido:
                peso_liq_caixa = float(row['Peso Liq CAIXA'])
                peso_liquido_calculado = peso_liq_caixa * qtd_caixas_valor

                results.append({
                    'referencia': row['referencia'],
                    'descricao': row['DESCRICAO'],
                    'quantidade': qtd_por_palete,
                    'qtd_caixas': qtd_caixas_valor,
                    'peso_bruto': peso_bruto_calculado,
                    'peso_liquido': peso_liquido_calculado,
                    'comprimento': float(row['COMPR. (CM)']),
                    'largura': float(row['LARGURA (CM)']),
                    'altura': float(row['ALTURA (CM)'])
                })



            if resto > 0:
                caixas_faltando = (resto // qtd_pcs_caixa) + (1 if resto % qtd_pcs_caixa > 0 else 0)
                caixas_restantes += caixas_faltando

                while caixas_restantes >= qtd_caixas:
                    results.append({
                        'referencia': row['referencia'],
                        'descricao': row['DESCRICAO'],
                        'quantidade': qtd_por_palete,
                        'qtd_caixas': qtd_caixas,
                        'peso_bruto': float(row['P. BRUTO']),
                        'peso_liquido': float(row['P. LÍQUIDO']),
                        'comprimento': float(row['COMPR. (CM)']),
                        'largura': float(row['LARGURA (CM)']),
                        'altura': float(row['ALTURA (CM)'])
                    })
                    caixas_restantes -= qtd_caixas

                if caixas_restantes > 0:
                    altura_calculada = ceil(caixas_restantes / 5) * float(row['ALT. CAIXA (CM)']) + 13

                    # Cálculo atualizado para o peso líquido:
                    peso_liq_caixa = float(row['Peso Liq CAIXA'])
                    peso_liquido_calculado = peso_liq_caixa * caixas_restantes

                    # Cálculo do peso bruto continua como antes, separando peso fixo e variável:
                    peso_fixo = float(row['Peso Pallet madeira']) \
                                + float(row['Peso da Tampa']) \
                                + float(row['Peso da cantoneira']) \
                                + float(row['Peso Stretch + Fita Arquear'])
                    peso_variavel = float(row['Peso Caixa com peça']) * caixas_restantes

                    novo_palete = {
                        'referencia': row['referencia'],
                        'descricao': row['DESCRICAO'],
                        'quantidade': resto,
                        'qtd_caixas': caixas_restantes,
                        'peso_bruto': peso_fixo + peso_variavel,
                        'peso_variavel': peso_variavel,
                        'peso_fixo': peso_fixo,
                        'peso_liquido': peso_liquido_calculado,
                        'comprimento': float(row['COMPR. (CM)']),
                        'largura': float(row['LARGURA (CM)']),
                        'altura': altura_calculada
                    }
                    paletes_quebrados_result.append(novo_palete)


        return results, paletes_quebrados_result

    except Exception as e:
        return f"Erro: {e}"

def deletar_linha_por_id(row_id):
    found = False
    for i, row in enumerate(st.session_state.linhas):
        if row.get("id") == row_id:
            st.session_state.linhas.pop(i)
            found = True
            break
    for i, row in enumerate(st.session_state.paletes_quebrados):
        if row.get("id") == row_id:
            st.session_state.paletes_quebrados.pop(i)
            found = True
            break
    return found

def atualizar_quantidade_por_id(row_id, new_quantity):
    updated = False
    for i, row in enumerate(st.session_state.linhas):
        if row.get("id") == row_id:
            st.session_state.linhas[i]['quantidade'] = new_quantity
            updated = True
            break
    if not updated:
        for index, item in enumerate(st.session_state.paletes_quebrados):
            if item.get("mix_group", False):
                for j, sub in enumerate(item["items"]):
                    if sub.get("id") == row_id:
                        st.session_state.paletes_quebrados[index]["items"][j]['quantidade'] = new_quantity
                        updated = True
                        break
                if updated:
                    break
            else:
                if item.get("id") == row_id:
                    st.session_state.paletes_quebrados[index]['quantidade'] = new_quantity
                    updated = True
                    break
    return updated

def salvar_dados_pdf(cabecalho, linhas, paletes_quebrados):
    try:
        if not linhas and not paletes_quebrados:
            return "Nenhum dado para salvar!"

        line_spacing = 25

        week_number = datetime.strptime(cabecalho['data'], '%Y-%m-%d').isocalendar()[1]
        pdf_file_path = os.path.join(
            SAVE_PATH, 
            f"Preparacao_Cargas_Pallet_Sem: {week_number}_{cabecalho['numeroPedido']}.pdf"
        )

        c = canvas.Canvas(pdf_file_path, pagesize=landscape(letter))
        width, height = landscape(letter)  # width=792, height=612
        y_position = height - 40
        MARGIN_BOTTOM = 50
        max_chars = 20

        # Margem e gap entre colunas
        margin = 30
        gap = 5

        # Definindo larguras para cada coluna.
        col_widths = [100, 20, 150, 60, 50, 70, 60, 50, 50, 50, 50]

        # Calcula as posições X cumulativas:
        x_ref         = margin
        x_ok          = x_ref + col_widths[0] + gap
        x_desc        = x_ok + col_widths[1] + gap
        x_qtd         = x_desc + col_widths[2] + gap
        x_peso_bruto  = x_qtd + col_widths[3] + gap
        x_peso_liq    = x_peso_bruto + col_widths[4] + gap
        x_compr       = x_peso_liq + col_widths[5] + gap
        x_larg        = x_compr + col_widths[6] + gap
        x_alt         = x_larg + col_widths[7] + gap
        x_qtd_caixas  = x_alt + col_widths[8] + gap
        x_palete      = x_qtd_caixas + col_widths[9] + gap

        def nova_pagina():
            nonlocal y_position
            c.showPage()
            y_position = height - 40
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_ref, y_position, "Referência")
            c.drawString(x_ok, y_position, "OK")
            c.drawString(x_desc, y_position, "Descrição")
            c.drawString(x_qtd, y_position, "Qtd")
            c.drawString(x_peso_bruto, y_position, "Peso Bruto")
            c.drawString(x_peso_liq, y_position, "Peso Líquido")
            c.drawString(x_compr, y_position, "Comprimento")
            c.drawString(x_larg, y_position, "Largura")
            c.drawString(x_alt, y_position, "Altura")
            c.drawString(x_qtd_caixas, y_position, "Qtd Caixas")
            c.drawString(x_palete, y_position, "Palete")
            y_position -= line_spacing
            c.setFont("Helvetica", 10)

        # Cabeçalho do PDF
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_ref, y_position, f"Solicitação: Preparação de materiais EXPORTAÇÃO: SEMANA: {week_number}")
        y_position -= line_spacing
        c.drawString(x_ref, y_position, f"Sold To: {cabecalho['soldTo']} {cabecalho['nomeCliente']}")
        y_position -= line_spacing
        c.drawString(x_ref, y_position, f"Data: {cabecalho['data']}")
        y_position -= (line_spacing + 5)

        # Cabeçalho da Tabela
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_ref, y_position, "Referência")
        c.drawString(x_ok, y_position, "OK")
        c.drawString(x_desc, y_position, "Descrição")
        c.drawString(x_qtd, y_position, "Qtd")
        c.drawString(x_peso_bruto, y_position, "Peso Bruto")
        c.drawString(x_peso_liq, y_position, "Peso Líquido")
        c.drawString(x_compr, y_position, "Comprimento")
        c.drawString(x_larg, y_position, "Largura")
        c.drawString(x_alt, y_position, "Altura")
        c.drawString(x_qtd_caixas, y_position, "Qtd Caixas")
        c.drawString(x_palete, y_position, "Palete")
        y_position -= line_spacing

        pallet_counter = 1

        # Itens dos Paletes Completos
        c.setFont("Helvetica", 10)
        for linha in linhas:
            if y_position < MARGIN_BOTTOM:
                nova_pagina()
            c.drawString(x_ref, y_position, str(linha['referencia']))
            c.rect(x_ok, y_position - 5, 8, 8, stroke=1, fill=0)
            descricao_text = linha['descricao']
            if len(descricao_text) > max_chars:
                descricao_text = descricao_text[:max_chars] + "..."
            c.setFont("Helvetica", 8)
            c.drawString(x_desc, y_position, descricao_text)
            c.setFont("Helvetica", 10)
            c.drawString(x_qtd, y_position, format_num(linha['quantidade']))
            c.drawString(x_peso_bruto, y_position, format_num(linha['peso_bruto']))
            c.drawString(x_peso_liq, y_position, format_num(linha['peso_liquido']))
            c.drawString(x_compr, y_position, format_num(linha['comprimento']))
            c.drawString(x_larg, y_position, format_num(linha['largura']))
            c.drawString(x_alt, y_position, format_num(linha['altura']))
            c.drawString(x_qtd_caixas, y_position, format_num(linha['qtd_caixas']))
            c.drawString(x_palete, y_position, f"Pal {pallet_counter:02d}")
            pallet_counter += 1
            y_position -= line_spacing

        # Itens dos Paletes Quebrados / Misto
        if paletes_quebrados:
            if y_position < MARGIN_BOTTOM:
                nova_pagina()
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_ref, y_position, "PALETE QUEBRADO/MISTO")
            y_position -= line_spacing
            for group in paletes_quebrados:
                if group.get("mix_group", False):
                    # Atribui um número único para o grupo mix
                    current_pal_number = f"Pal {pallet_counter:02d}"
                    pallet_counter += 1
                    # Calcula a área necessária para o grupo
                    n_items = len(group["items"])
                    group_box_top = y_position
                    group_box_bottom = group_box_top - n_items * line_spacing
                    padding_top = 15      # padding superior
                    padding_bottom = -15   # padding inferior
                    adjusted_top = group_box_top + padding_top
                    adjusted_bottom = group_box_bottom - padding_bottom
                    rect_height = adjusted_top - adjusted_bottom
                    rectangle_margin = 10  
                    rect_width = width - 2 * rectangle_margin
                    # Desenha um retângulo cinza atrás do grupo
                    c.setLineWidth(1)
                    c.setFillColorRGB(0.9, 0.9, 0.9)
                    c.rect(rectangle_margin, adjusted_bottom, rect_width, rect_height, stroke=1, fill=1)
                    c.setFillColorRGB(0, 0, 0)
                    for sub in group["items"]:
                        if y_position < MARGIN_BOTTOM:
                            nova_pagina()
                        c.setFont("Helvetica", 10)
                        c.drawString(x_ref, y_position, str(sub['referencia']))
                        c.rect(x_ok, y_position - 5, 8, 8, stroke=1, fill=0)
                        descricao_text = sub['descricao']
                        if len(descricao_text) > max_chars:
                            descricao_text = descricao_text[:max_chars] + "..."
                        c.setFont("Helvetica", 8)
                        c.drawString(x_desc, y_position, descricao_text)
                        c.setFont("Helvetica", 10)
                        c.drawString(x_qtd, y_position, format_num(sub['quantidade']))
                        c.drawString(x_peso_bruto, y_position, format_num(sub['peso_bruto']))
                        c.drawString(x_peso_liq, y_position, format_num(sub['peso_liquido']))
                        c.drawString(x_compr, y_position, format_num(sub['comprimento']))
                        c.drawString(x_larg, y_position, format_num(sub['largura']))
                        c.drawString(x_alt, y_position, format_num(sub['altura']))
                        c.drawString(x_qtd_caixas, y_position, format_num(sub['qtd_caixas']))
                        c.drawString(x_palete, y_position, current_pal_number)
                        y_position -= line_spacing
                    # Ajusta a posição para a próxima linha após o grupo
                    y_position = group_box_bottom - (line_spacing - padding_bottom)
                else:
                    if y_position < MARGIN_BOTTOM:
                        nova_pagina()
                    c.setFont("Helvetica", 10)
                    c.drawString(x_ref, y_position, str(group['referencia']))
                    c.rect(x_ok, y_position - 5, 8, 8, stroke=1, fill=0)
                    descricao_text = group['descricao']
                    if len(descricao_text) > max_chars:
                        descricao_text = descricao_text[:max_chars] + "..."
                    c.setFont("Helvetica", 8)
                    c.drawString(x_desc, y_position, descricao_text)
                    c.setFont("Helvetica", 10)
                    c.drawString(x_qtd, y_position, format_num(group['quantidade']))
                    c.drawString(x_peso_bruto, y_position, format_num(group['peso_bruto']))
                    c.drawString(x_peso_liq, y_position, format_num(group['peso_liquido']))
                    c.drawString(x_compr, y_position, format_num(group['comprimento']))
                    c.drawString(x_larg, y_position, format_num(group['largura']))
                    c.drawString(x_alt, y_position, format_num(group['altura']))
                    c.drawString(x_qtd_caixas, y_position, format_num(group['qtd_caixas']))
                    c.drawString(x_palete, y_position, f"Pal {pallet_counter:02d}")
                    pallet_counter += 1
                    y_position -= line_spacing

        # Rodapé: informações gerais
        general_info_height = 5 * line_spacing + 30
        group_comprimento = {}
        group_largura = {}
        group_altura = {}
        for item in linhas:
            comp = item.get('comprimento')
            larg = item.get('largura')
            alt = item.get('altura')
            if comp is not None:
                group_comprimento[comp] = group_comprimento.get(comp, 0) + 1
            if larg is not None:
                group_largura[larg] = group_largura.get(larg, 0) + 1
            if alt is not None:
                group_altura[alt] = group_altura.get(alt, 0) + 1
        for item in paletes_quebrados:
            if item.get("mix_group", False):
                try:
                    mix_altura = sum(float(sub['altura']) for sub in item["items"]) - 25
                except Exception:
                    mix_altura = None
                first_item = item["items"][0] if item["items"] else {}
                comp = first_item.get('comprimento')
                larg = first_item.get('largura')
                if comp is not None:
                    group_comprimento[comp] = group_comprimento.get(comp, 0) + 1
                if larg is not None:
                    group_largura[larg] = group_largura.get(larg, 0) + 1
                if mix_altura is not None and mix_altura > 98:
                    mix_altura = 98
                if mix_altura is not None:
                    mix_altura_str = format_num(mix_altura)
                    group_altura[mix_altura_str] = group_altura.get(mix_altura_str, 0) + 1
            else:
                comp = item.get('comprimento')
                larg = item.get('largura')
                alt = item.get('altura')
                if comp is not None:
                    group_comprimento[comp] = group_comprimento.get(comp, 0) + 1
                if larg is not None:
                    group_largura[larg] = group_largura.get(larg, 0) + 1
                if alt is not None:
                    group_altura[alt] = group_altura.get(alt, 0) + 1

        col1_text = ["Distribuição de COMPRIMENTO (CM):"] + [f"{comp} cm: {count} paletes" for comp, count in group_comprimento.items()]
        col2_text = ["Distribuição de LARGURA (CM):"] + [f"{larg} cm: {count} paletes" for larg, count in group_largura.items()]
        col3_text = ["Distribuição de ALTURA (CM):"] + [f"{alt} cm: {count} paletes" for alt, count in group_altura.items()]
        max_rows = max(len(col1_text), len(col2_text), len(col3_text))
        distribution_block_height = max_rows * line_spacing
        total_footer_block_height = general_info_height + distribution_block_height

        if y_position - total_footer_block_height < MARGIN_BOTTOM:
            nova_pagina()

        c.setLineWidth(1)
        c.line(x_ref, y_position, width - margin, y_position)
        y_position -= (line_spacing - 5)

        # Converte os valores para float na hora da soma
        total_pecas = sum(float(item['quantidade']) for item in linhas)
        peso_bruto_total = sum(float(item['peso_bruto']) for item in linhas)
        peso_liquido_total = sum(float(item['peso_liquido']) for item in linhas)
        total_caixas = sum(float(item['qtd_caixas']) for item in linhas)
        total_palets = len(linhas)
        for item in paletes_quebrados:
            if item.get("mix_group", False):
                for sub in item["items"]:
                    total_pecas += float(sub['quantidade'])
                    peso_bruto_total += float(sub['peso_bruto'])
                    peso_liquido_total += float(sub['peso_liquido'])
                    total_caixas += float(sub['qtd_caixas'])
                total_palets += 1
            else:
                total_pecas += float(item['quantidade'])
                peso_bruto_total += float(item['peso_bruto'])
                peso_liquido_total += float(item['peso_liquido'])
                total_caixas += float(item['qtd_caixas'])
                total_palets += 1

        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_ref, y_position, "INFORMAÇÕES GERAIS DA CARGA:")
        y_position -= line_spacing

        c.setFont("Helvetica", 10)
        c.drawString(x_ref, y_position, f"TOTAL PEÇAS: {format_num(total_pecas)}")
        c.drawString(250, y_position, f"TOTAL PALLETS: {total_palets}")
        c.drawRightString(width - margin, y_position, f"Número do Pedido: {cabecalho['numeroPedido']}")
        y_position -= line_spacing

        c.drawString(x_ref, y_position, f"PESO BRUTO TOTAL: {format_num(peso_bruto_total)}")
        y_position -= line_spacing

        c.drawString(x_ref, y_position, f"PESO LÍQUIDO TOTAL: {format_num(peso_liquido_total)}")
        y_position -= line_spacing

        c.drawString(x_ref, y_position, f"TOTAL CAIXAS: {format_num(total_caixas)}")
        y_position -= (line_spacing + 5)

        distribution_start_y = y_position
        col_width = (width - 2 * margin) / 3
        x1_d = margin
        x2_d = margin + col_width
        x3_d = margin + 2 * col_width

        for i in range(max_rows):
            current_y = distribution_start_y - i * line_spacing
            if i < len(col1_text):
                c.drawString(x1_d, current_y, col1_text[i])
            if i < len(col2_text):
                c.drawString(x2_d, current_y, col2_text[i])
            if i < len(col3_text):
                c.drawString(x3_d, current_y, col3_text[i])

        c.save()
        return pdf_file_path

    except Exception as e:
        return f"Erro ao salvar os dados: {e}"