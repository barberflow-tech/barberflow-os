import smtplib
from unittest.mock import patch

import pytest
from django.core import mail

from apps.notificaciones.models import EmailDelivery
from apps.notificaciones.services import send_notification_email

pytestmark = pytest.mark.django_db


def test_sends_email_and_records_delivery(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "BarberFlow <notificaciones@barberflow.test>"
    html_body = "<p>Tu cita es mañana a las 10:00.</p>"

    delivery = send_notification_email(
        recipient="cliente@example.com",
        subject="Tu cita en BarberFlow",
        body="Tu cita es mañana a las 10:00.",
        html_body=html_body,
    )

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert message.to == [delivery.recipient]
    assert message.subject == delivery.subject
    assert message.body == "Tu cita es mañana a las 10:00."
    assert message.alternatives == [(html_body, "text/html")]

    delivery.refresh_from_db()
    assert delivery.status == EmailDelivery.Status.SENT
    assert delivery.sent_at >= delivery.created_at
    assert delivery.error_code == ""


def test_records_smtp_failure_without_raising(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch(
        "smtplib.SMTP",
        side_effect=smtplib.SMTPAuthenticationError(535, b"private provider response"),
    ):
        delivery = send_notification_email(
            recipient="cliente@example.com",
            subject="Tu cita en BarberFlow",
            body="Recordatorio de cita",
        )

    delivery.refresh_from_db()
    assert delivery.status == EmailDelivery.Status.FAILED
    assert delivery.sent_at is None
    assert delivery.error_code == "SMTPAuthenticationError"


def test_records_failure_when_backend_reports_no_send(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

    with patch(
        "django.core.mail.backends.dummy.EmailBackend.send_messages", return_value=0
    ):
        delivery = send_notification_email(
            recipient="cliente@example.com",
            subject="Tu cita en BarberFlow",
            body="Recordatorio de cita",
        )

    delivery.refresh_from_db()
    assert delivery.status == EmailDelivery.Status.FAILED
    assert delivery.sent_at is None
    assert delivery.error_code == "not_sent"
