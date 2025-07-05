import imaplib
import email
from email.header import decode_header
import os

# === CONFIGURAÇÕES ===
EMAIL_USUARIO = "marcio.moraes@autoliv.com"
EMAIL_SENHA = "@autoliv2940"
IMAP_SERVIDOR = "imap.office365.com"  # Outlook corporativo usa geralmente este
PASTA_DESTINO = "anexos_salvos"

# Cria a pasta local para salvar anexos
os.makedirs(PASTA_DESTINO, exist_ok=True)

# Conecta ao servidor
mail = imaplib.IMAP4_SSL(IMAP_SERVIDOR)
mail.login(EMAIL_USUARIO, EMAIL_SENHA)
mail.select("inbox")

# Filtra e-mails com anexo (ou por remetente, assunto, etc)
status, mensagens = mail.search(None, 'ALL')  # você pode mudar para: (FROM "scanner@autoliv.com")

email_ids = mensagens[0].split()

for num in email_ids:
    status, dados = mail.fetch(num, "(RFC822)")
    raw_email = dados[0][1]
    msg = email.message_from_bytes(raw_email)

    for parte in msg.walk():
        if parte.get_content_maintype() == 'multipart':
            continue
        if parte.get('Content-Disposition') is None:
            continue

        nome_arquivo = parte.get_filename()
        if nome_arquivo:
            nome_arquivo, encoding = decode_header(nome_arquivo)[0]
            if isinstance(nome_arquivo, bytes):
                nome_arquivo = nome_arquivo.decode(encoding or 'utf-8')

            caminho = os.path.join(PASTA_DESTINO, nome_arquivo)
            with open(caminho, 'wb') as f:
                f.write(parte.get_payload(decode=True))
            print(f"Anexo salvo: {caminho}")

# Encerra a conexão
mail.logout()
