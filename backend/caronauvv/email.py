"""
ENVIO DE E-MAIL

- Com MAIL_SERVER configurado no .env: envia de verdade por SMTP (ex.: Gmail, Outlook).
- Sem MAIL_SERVER (desenvolvimento / apresentacao): o e-mail e escrito no log
  do Flask, e nada sai da maquina.
"""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger("caronauvv")


def enviar_email(destino: str, assunto: str, texto: str) -> bool:
    """Envia (ou registra no log) um e-mail simples. Devolve True se saiu por SMTP."""
    cfg = current_app.config
    if not cfg.get("MAIL_SERVER"):
        logger.info("E-MAIL (modo desenvolvimento, nao enviado) para %s | %s | %s", destino, assunto, texto)
        return False

    msg = EmailMessage()
    msg["From"] = cfg.get("MAIL_FROM") or cfg.get("MAIL_USERNAME")
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.set_content(texto)
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg.get("MAIL_PORT", 587), timeout=10) as smtp:
            smtp.starttls()
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
            smtp.send_message(msg)
        logger.info("E-mail enviado para %s (%s)", destino, assunto)
        return True
    except (OSError, smtplib.SMTPException):
        # Falha de e-mail nao derruba o cadastro: o aluno pode pedir outro codigo
        logger.exception("Falha ao enviar e-mail para %s", destino)
        return False
