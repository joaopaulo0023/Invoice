import streamlit as st
from streamlit_drawable_canvas import st_canvas
import fitz  # PyMuPDF
import os

def adicionar_texto_no_pdf(input_pdf, output_pdf, texto, pos_x, pos_y, pagina=0):
    """
    Adiciona texto em coordenadas específicas (X, Y) de uma página do PDF.
    """
    try:
        pdf_document = fitz.open(input_pdf)
        if pagina >= len(pdf_document):
            return False, f"O PDF tem apenas {len(pdf_document)} páginas."

        # Inverte a posição Y para corresponder ao PDF (origem no canto inferior esquerdo)
        page = pdf_document[pagina]
        page_height = page.rect.height
        inverted_y = page_height - pos_y

        # Adiciona o texto
        page.insert_text((pos_x, inverted_y), texto, fontsize=12, color=(0, 0, 0))
        pdf_document.save(output_pdf)
        pdf_document.close()
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    st.set_page_config(page_title="Editor PDF com Captura de Clique", layout="wide")
    st.title("Editor de PDF - Adicionar Texto via Clique")
    st.write("Carregue um PDF, clique para fornecer as coordenadas e baixe o PDF modificado.")

    # Upload do arquivo PDF
    uploaded_file = st.file_uploader("Carregue seu PDF", type=["pdf"])
    
    if uploaded_file is not None:
        input_pdf = "input_temp.pdf"
        with open(input_pdf, "wb") as f:
            f.write(uploaded_file.read())

        # Renderiza a imagem do PDF na tela
        pdf_document = fitz.open(input_pdf)
        page = pdf_document[0]
        image = page.get_pixmap()
        output_image_path = "page_preview.png"
        image.save(output_image_path)

        st.subheader("Clique na imagem para fornecer as coordenadas:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=3,
            stroke_color="#000000",
            background_image=st.image(output_image_path),
            update_streamlit=True,
            height=image.height,
            width=image.width,
            drawing_mode="point",
            key="canvas",
        )

        if canvas_result.json_data is not None:
            # Captura a posição X e Y do clique
            for obj in canvas_result.json_data["objects"]:
                if obj["type"] == "circle":  # Detecta o ponto do clique
                    pos_x = obj["left"]
                    pos_y = obj["top"]

                    st.success(f"Coordenadas capturadas: X={pos_x}, Y={pos_y}")

                    # Solicita o texto a ser adicionado
                    texto = st.text_input("Texto a ser adicionado:", "Exemplo de Texto")
                    
                    if st.button("Adicionar Texto e Gerar PDF"):
                        output_pdf = "output_temp.pdf"
                        sucesso, erro = adicionar_texto_no_pdf(input_pdf, output_pdf, texto, pos_x, pos_y, 0)
                        if sucesso:
                            st.success("Texto adicionado com sucesso! Baixe o PDF abaixo.")
                            with open(output_pdf, "rb") as file:
                                st.download_button(
                                    label="📥 Baixar PDF Editado",
                                    data=file,
                                    file_name="pdf_editado.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.error(f"Erro: {erro}")
        
        # Limpeza de arquivos temporários
        if os.path.exists(input_pdf):
            os.remove(input_pdf)
        if os.path.exists("output_temp.pdf"):
            os.remove("output_temp.pdf")
        if os.path.exists("page_preview.png"):
            os.remove("page_preview.png")

if __name__ == "__main__":
    main()






