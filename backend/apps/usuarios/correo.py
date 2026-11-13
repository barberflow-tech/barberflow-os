"""Envio de correo transaccional con el backend de correo de Django (SMTP).

El proveedor se elige solo por variables de entorno (EMAIL_HOST, ...): Gmail con
contrasena de aplicacion, Resend o Brevo por SMTP, etc. Sin EMAIL_HOST el correo
se imprime en el log, que es lo que se usa en local.
"""

import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def enviar_correo(destino: str, asunto: str, html: str, texto: str) -> bool:
    """Envia un correo. True si el servidor lo acepto, False si no.

    Nunca lanza: un fallo del servidor de correo no debe tumbar la peticion (ni
    revelar si el correo existe). Se registra en el log.
    """
    mensaje = EmailMultiAlternatives(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, [destino]
    )
    mensaje.attach_alternative(html, "text/html")
    try:
        mensaje.send()
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("No se pudo enviar el correo a %s: %s", destino, exc)
        return False


def enviar_recuperacion_contrasena(destino: str, enlace: str, minutos: int) -> bool:
    """Correo con el enlace para restablecer la contrasena."""
    asunto = "Restablece tu contraseña de BarberFlow"
    texto = (
        "Recibimos una solicitud para restablecer tu contraseña de BarberFlow.\n\n"
        f"Abre este enlace (vale {minutos} minutos):\n{enlace}\n\n"
        "Si no fuiste tú, ignora este correo: tu contraseña no cambia."
    )
    html = f"""\
<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#111">
  <h2 style="margin:0 0 12px">Restablece tu contraseña</h2>
  <p>Recibimos una solicitud para restablecer tu contraseña de BarberFlow.</p>
  <p style="margin:24px 0">
    <a href="{enlace}" style="background:#d7b36a;color:#111;padding:12px 20px;
       border-radius:8px;text-decoration:none;font-weight:bold">Elegir nueva contraseña</a>
  </p>
  <p style="font-size:13px;color:#555">El enlace vale {minutos} minutos y solo se puede
  usar una vez. Si no fuiste tú, ignora este correo: tu contraseña no cambia.</p>
</div>"""
    return enviar_correo(destino, asunto, html, texto)
