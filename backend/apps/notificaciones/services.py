from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import EmailDelivery


def send_notification_email(
    *,
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> EmailDelivery:
    """Envía un aviso a un destinatario y devuelve el registro del intento.

    Si el proveedor falla, devuelve el registro con estado FAILED. Llama a
    este servicio después de confirmar cualquier transacción de negocio de
    la que dependa el aviso.
    """
    delivery = EmailDelivery.objects.create(recipient=recipient, subject=subject)
    message = EmailMultiAlternatives(subject=subject, body=body, to=[recipient])
    if html_body is not None:
        message.attach_alternative(html_body, "text/html")

    try:
        sent_count = message.send()
    except Exception as error:
        # El mensaje del proveedor puede contener credenciales o datos del aviso.
        delivery.error_code = type(error).__name__[:100]
        delivery.status = EmailDelivery.Status.FAILED
    else:
        if sent_count == 1:
            delivery.status = EmailDelivery.Status.SENT
            delivery.sent_at = timezone.now()
        else:
            delivery.status = EmailDelivery.Status.FAILED
            delivery.error_code = "not_sent"

    delivery.save(update_fields=["status", "sent_at", "error_code"])
    return delivery
