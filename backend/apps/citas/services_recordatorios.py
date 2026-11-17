"""Recordatorios de citas a las 24 h y 2 h (HU-05 / SCRUM-63).

La logica de negocio vive aqui y no en el comando: el comando solo llama a
`enviar_recordatorios` y muestra el resumen.

Ventanas: el aviso de 24 h sale cuando faltan MAS de 23 h 30 min y hasta 24 h; el
de 2 h, cuando faltan mas de 1 h 30 min y hasta 2 h. El margen de gracia
(`MARGEN_DE_GRACIA`) cubre varias ejecuciones del cron y los reintentos tras un
fallo del proveedor. Una cita reservada (o movida) cuando ya paso su ventana no
recibe ese aviso: nadie recibe un "faltan 24 horas" al instante de reservar.

Sin duplicados, en tres capas: (1) la busqueda excluye lo ya enviado; (2) cada
cita se procesa con su fila bloqueada, asi que dos ejecuciones simultaneas no la
procesan a la vez; (3) `RecordatorioCita` tiene una restriccion unica por
(cita, tipo, hora de la cita).

Concurrencia: se bloquea SOLO la fila de la cita, con SELECT ... FOR UPDATE
SKIP LOCKED. Es el mismo recurso que bloquea `cancelar_cita`, y menos que
`reprogramar_cita` (cita -> barbero) y `crear_cita` (barbero), asi que no puede
formar un ciclo de espera. Con la cita bloqueada se releen su estado y su hora:
una cancelacion o reprogramacion que llego entre la busqueda y el envio se
respeta. A cambio, la cita queda bloqueada mientras dura el envio (el timeout de
correo es de segundos). Si el proceso muere justo despues de enviar y antes del
COMMIT, el siguiente ciclo repetiria ese correo (garantia "al menos una vez").
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import DatabaseError, models, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.html import escape

from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.notificaciones.models import EmailDelivery
from apps.notificaciones.services import send_notification_email

from .models import Cita, RecordatorioCita
from .services import _correo_de

logger = logging.getLogger(__name__)

Tipo = RecordatorioCita.Tipo

# Se recuerdan las citas activas: las PENDING (todas las que hoy crea la reserva)
# y las CONFIRMED. Las canceladas, completadas y no-show nunca reciben aviso.
ESTADOS_RECORDABLES = (Cita.Estado.PENDING, Cita.Estado.CONFIRMED)

# Antelacion de cada aviso y margen de gracia de su ventana.
ANTELACION_DEL_AVISO = {
    Tipo.REMINDER_24H: timedelta(hours=24),
    Tipo.REMINDER_2H: timedelta(hours=2),
}
MARGEN_DE_GRACIA = timedelta(minutes=30)

_TEXTO_ANTELACION = {Tipo.REMINDER_24H: "24 horas", Tipo.REMINDER_2H: "2 horas"}


class ResultadoAviso(models.TextChoices):
    """Que paso al procesar una cita."""

    ENVIADO = "ENVIADO", "Enviado"
    FALLIDO = "FALLIDO", "Fallido"
    SIN_CANAL = "SIN_CANAL", "Sin correo"
    OMITIDO = "OMITIDO", "Omitido"


@dataclass
class ResumenRecordatorios:
    """Conteo de una ejecucion de la tarea programada."""

    enviados: int = 0
    fallidos: int = 0
    sin_canal: int = 0
    omitidos: int = 0
    errores: int = 0

    def registrar(self, resultado: str) -> None:
        if resultado == ResultadoAviso.ENVIADO:
            self.enviados += 1
        elif resultado == ResultadoAviso.FALLIDO:
            self.fallidos += 1
        elif resultado == ResultadoAviso.SIN_CANAL:
            self.sin_canal += 1
        else:
            self.omitidos += 1


def ventana_de_aviso(tipo: str, ahora: datetime) -> tuple[datetime, datetime]:
    """(desde, hasta) de la ventana del aviso: desde exclusivo, hasta inclusivo.

    Se calcula en UTC: sumar horas a una fecha con zona (zoneinfo) suma "hora de
    pared", y en un dia de cambio de hora 24 h de pared no son 24 h reales. Una
    fecha sin zona es ambigua y se rechaza.
    """
    if timezone.is_naive(ahora):
        raise ValueError("`ahora` debe incluir zona horaria.")
    limite = ahora.astimezone(dt_timezone.utc) + ANTELACION_DEL_AVISO[tipo]
    return limite - MARGEN_DE_GRACIA, limite


def _debe_recordarse(cita: Cita, tipo: str, ahora: datetime) -> bool:
    desde, hasta = ventana_de_aviso(tipo, ahora)
    return cita.status in ESTADOS_RECORDABLES and desde < cita.start_at <= hasta


def buscar_citas_a_recordar(tipo: str, ahora: datetime):
    """Citas activas dentro de la ventana del aviso y sin ese aviso ya enviado.

    Incluye las de visitantes: se cuentan como "sin canal" al procesarlas.
    """
    desde, hasta = ventana_de_aviso(tipo, ahora)
    ya_enviado = RecordatorioCita.objects.filter(
        appointment=OuterRef("pk"),
        reminder_type=tipo,
        appointment_start_at=OuterRef("start_at"),
        sent_at__isnull=False,
    )
    return (
        Cita.objects.filter(
            status__in=ESTADOS_RECORDABLES, start_at__gt=desde, start_at__lte=hasta
        )
        .exclude(Exists(ya_enviado))
        .select_related("client", "service", "barber")
        .order_by("start_at", "pk")
    )


def _asunto_y_cuerpo_recordatorio(cita: Cita, tipo: str) -> tuple[str, str, str]:
    """Asunto, texto plano y HTML del recordatorio. La hora va en Bogota.

    Aislada para sustituirla por la plantilla definitiva de SCRUM-65 sin tocar
    el resto del flujo.
    """
    inicio = cita.start_at.astimezone(ZONA_HORARIA_BARBERIA)
    fecha, hora = f"{inicio:%d/%m/%Y}", f"{inicio:%H:%M}"
    precio = "$" + f"{cita.price:,.0f}".replace(",", ".")
    enlace = f"{settings.FRONTEND_URL}/perfil"
    faltan = _TEXTO_ANTELACION[tipo]

    asunto = f"Recordatorio: tu cita del {fecha} a las {hora}"
    texto = (
        f"Hola,\n\nFaltan {faltan} para tu cita en BarberFlow.\n\n"
        f"Servicio: {cita.service.name}\n"
        f"Barbero: {cita.barber.name}\n"
        f"Fecha: {fecha}\n"
        f"Hora: {hora}\n"
        f"Precio: {precio}\n\n"
        f"Puedes verla, reprogramarla o cancelarla en Mis citas: {enlace}"
    )
    html = (
        '<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto">'
        f"<h2>Faltan {faltan} para tu cita</h2>"
        f"<p><b>Servicio:</b> {escape(cita.service.name)}<br>"
        f"<b>Barbero:</b> {escape(cita.barber.name)}<br>"
        f"<b>Fecha:</b> {fecha}<br><b>Hora:</b> {hora}<br>"
        f"<b>Precio:</b> {precio}</p>"
        f'<p><a href="{escape(enlace)}">Ver mis citas</a></p></div>'
    )
    return asunto, texto, html


def enviar_recordatorio_de_cita(
    *, cita_id: int, tipo: str, ahora: datetime
) -> ResultadoAviso:
    """Procesa una cita: revalida, envia y registra el intento.

    Con la fila de la cita bloqueada (SKIP LOCKED) se releen su estado y su hora;
    si ya no esta activa o salio de la ventana, no se envia nada. El destinatario
    es el correo del cliente con cuenta; un visitante no tiene correo. Un fallo
    del proveedor deja el intento registrado y el aviso pendiente de reintento.
    """
    with transaction.atomic():
        cita = (
            Cita.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("client", "service", "barber")
            .filter(pk=cita_id)
            .first()
        )
        if cita is None or not _debe_recordarse(cita, tipo, ahora):
            return ResultadoAviso.OMITIDO

        correo = _correo_de(cita)
        if not correo:
            return ResultadoAviso.SIN_CANAL

        registro, _ = RecordatorioCita.objects.get_or_create(
            appointment=cita,
            reminder_type=tipo,
            appointment_start_at=cita.start_at,
        )
        if registro.sent_at is not None:
            return ResultadoAviso.OMITIDO

        asunto, texto, html = _asunto_y_cuerpo_recordatorio(cita, tipo)
        entrega = send_notification_email(
            recipient=correo, subject=asunto, body=texto, html_body=html
        )
        registro.attempts += 1
        registro.delivery = entrega
        if entrega.status == EmailDelivery.Status.SENT:
            registro.sent_at = entrega.sent_at or timezone.now()
        registro.save(update_fields=["attempts", "delivery", "sent_at"])

    return ResultadoAviso.ENVIADO if registro.sent_at else ResultadoAviso.FALLIDO


def enviar_recordatorios(*, ahora: datetime | None = None) -> ResumenRecordatorios:
    """Envia los recordatorios de 24 h y 2 h que correspondan en este momento.

    Es idempotente: se puede ejecutar cuantas veces se quiera (cron cada 10 min)
    sin duplicar avisos. `ahora` se inyecta en las pruebas para simular el tiempo.
    Un error de base de datos en una cita se registra, se cuenta y no impide
    procesar las demas.
    """
    momento = ahora if ahora is not None else timezone.now()
    resumen = ResumenRecordatorios()

    for tipo in Tipo:
        ids = list(buscar_citas_a_recordar(tipo, momento).values_list("pk", flat=True))
        for cita_id in ids:
            try:
                resultado = enviar_recordatorio_de_cita(
                    cita_id=cita_id, tipo=tipo, ahora=momento
                )
            except DatabaseError:
                logger.exception(
                    "Fallo al enviar el recordatorio de la cita %s", cita_id
                )
                resumen.errores += 1
                continue
            resumen.registrar(resultado)

    return resumen
