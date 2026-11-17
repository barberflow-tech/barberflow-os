"""Casos de uso de citas.

La logica de negocio vive aqui y no en las views: la view (siguiente paso
de HU-02) solo traduce HTTP <-> llamadas a este modulo.
"""

from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.jornada import (
    MOTIVO_EN_DESCANSO,
    ZONA_HORARIA_BARBERIA,
    motivo_franja_fuera_de_jornada,
    obtener_jornada_barbero,
)
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.notificaciones.models import EmailDelivery
from apps.notificaciones.services import send_notification_email

from .models import BloqueoAgenda, Cita

RESTRICCION_SOLAPAMIENTO = "cita_sin_solapamiento_por_barbero"

# HU-03: con la antelacion minima o menos una cancelacion es tardia (HU-19) y la
# reprogramacion no se permite. "Mas de N h" es estricto: N h justas no basta.
# El valor sale de settings (CITAS_ANTICIPACION_MINIMA_HORAS) para cambiarlo en
# un solo lugar.
ANTICIPACION_MINIMA_HORAS = settings.CITAS_ANTICIPACION_MINIMA_HORAS
ANTICIPACION_MINIMA = timedelta(hours=ANTICIPACION_MINIMA_HORAS)
_TEXTO_ANTICIPACION = (
    "1 hora" if ANTICIPACION_MINIMA_HORAS == 1 else f"{ANTICIPACION_MINIMA_HORAS} horas"
)
MENSAJE_REPROGRAMACION_TARDIA = (
    f"Solo puedes reprogramar con más de {_TEXTO_ANTICIPACION} de anticipación."
)
# Solo estas citas se pueden cancelar o reprogramar; el resto ya cerro su ciclo.
ESTADOS_MODIFICABLES = (Cita.Estado.PENDING, Cita.Estado.CONFIRMED)


class CitaError(Exception):
    """Error de negocio al gestionar una cita."""


class HorarioInvalidoError(CitaError):
    """La fecha/hora solicitada no es valida (sin zona horaria o en el pasado)."""


class RecursoInactivoError(CitaError):
    """El barbero o el servicio no existe o no esta activo."""


class FranjaNoDisponibleError(CitaError):
    """La franja se solapa con una cita activa o un bloqueo del barbero."""


class CitaNoEncontradaError(CitaError):
    """La cita no existe."""


class NoEsPropietarioError(CitaError):
    """El usuario no es el propietario de la cita (o la cita no tiene cuenta)."""


class EstadoCitaInvalidoError(CitaError):
    """La cita no se puede modificar: ya terminó su ciclo o ya empezó."""


class ReprogramacionTardiaError(CitaError):
    """Falta la antelacion minima o menos: ya no se puede reprogramar."""


def crear_cita(
    *,
    cliente,
    barberia: Barberia,
    barbero_id: int,
    servicio_id: int,
    inicio: datetime,
    contacto_nombre: str = "",
    contacto_celular: str = "",
) -> Cita:
    """Crea una cita en estado PENDING de forma atomica (HU-02).

    Bloquea la fila del barbero con SELECT ... FOR UPDATE, de modo que las
    reservas concurrentes de un mismo barbero se ejecutan de una en una, y
    revalida la disponibilidad ya con el bloqueo adquirido. Cualquier
    excepcion dentro del bloque atomico provoca ROLLBACK y libera el bloqueo.

    Barbero y servicio se buscan solo dentro de `barberia` (el tenant del
    usuario): un ID de otra barberia se trata igual que uno inexistente.

    `cliente` puede ser None (visitante sin cuenta); entonces el contacto
    (nombre y celular) es obligatorio.
    """
    if cliente is None and not (contacto_nombre and contacto_celular):
        raise HorarioInvalidoError("Falta el nombre o el celular de contacto.")
    # Validaciones  que no dependen del estado de la agenda.
    if timezone.is_naive(inicio):
        raise HorarioInvalidoError("La hora de inicio debe incluir zona horaria.")
    if inicio <= timezone.now():
        raise HorarioInvalidoError("La cita debe ser en el futuro.")

    try:
        with transaction.atomic():
            barbero = (
                Barbero.objects.select_for_update()
                .filter(pk=barbero_id, barberia=barberia)
                .first()
            )
            if barbero is None or not barbero.is_active:
                raise RecursoInactivoError("El barbero no esta disponible.")

            servicio = Servicio.objects.filter(
                pk=servicio_id, barberia=barberia, is_active=True
            ).first()
            if servicio is None:
                raise RecursoInactivoError("El servicio no esta disponible.")

            fin = inicio + timedelta(minutes=servicio.duration_minutes)

            # Con la fila bloqueada, se ven las citas y bloqueos confirmados
            # por las transacciones anteriores para el mismo barbero.
            if (
                Cita.objects.solapadas(barbero, inicio, fin).exists()
                or BloqueoAgenda.objects.solapados(barbero, inicio, fin).exists()
            ):
                raise FranjaNoDisponibleError(
                    "La franja seleccionada ya no esta disponible."
                )

            return Cita.objects.create(
                barberia=barberia,
                client=cliente,
                contact_name=contacto_nombre,
                contact_phone=contacto_celular,
                barber=barbero,
                service=servicio,
                start_at=inicio,
                end_at=fin,
                status=Cita.Estado.PENDING,
                price=servicio.price,
            )
    except IntegrityError as exc:
        # Se captura fuera del atomic: la transaccion ya hizo ROLLBACK.
        if _restriccion_violada(exc) == RESTRICCION_SOLAPAMIENTO:
            raise FranjaNoDisponibleError(
                "La franja seleccionada ya no esta disponible."
            ) from exc
        raise


def _restriccion_violada(exc: IntegrityError) -> str | None:
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)


def obtener_cita_id(cita_id: int) -> Cita:
    """Devuelve la cita con ese ID (sin bloqueo) o lanza CitaNoEncontradaError."""
    cita = Cita.objects.filter(pk=cita_id).first()
    if cita is None:
        raise CitaNoEncontradaError("La cita no existe.")
    return cita


def validar_propietario_cita(cita: Cita, usuario: AbstractBaseUser) -> None:
    """Solo el cliente que reservó con su cuenta puede gestionar la cita.

    Una cita de visitante (`client` nulo) no tiene propietario posible, así que
    nadie la gestiona por este camino.
    """
    if cita.client_id is None or cita.client_id != usuario.pk:
        raise NoEsPropietarioError("Solo el propietario de la cita puede gestionarla.")


def validar_estado_modificable(cita: Cita) -> None:
    """Solo las citas PENDING o CONFIRMED se pueden modificar."""
    if cita.status not in ESTADOS_MODIFICABLES:
        estado = cita.get_status_display().lower()
        raise EstadoCitaInvalidoError(
            f"La cita está {estado} y ya no se puede modificar."
        )


def validar_cita_no_iniciada(cita: Cita, ahora: datetime) -> None:
    """Una cita que ya empezó no se cancela: lo que sigue es asistencia o no-show."""
    if cita.start_at <= ahora:
        raise EstadoCitaInvalidoError("La cita ya empezó y no se puede cancelar.")


def tiene_anticipacion_minima(inicio: datetime, ahora: datetime) -> bool:
    """True si faltan MÁS de la antelacion minima para `inicio` (justa es False)."""
    return inicio - ahora > ANTICIPACION_MINIMA


def liberar_franja_horaria(cita: Cita, ahora: datetime) -> None:
    """Marca la cita como CANCELLED, lo que libera su franja en la agenda.

    No hay tabla de slots: la franja es el rango de una cita no cancelada, y
    tanto `Cita.objects.activas()` como la condición del ExclusionConstraint
    excluyen las CANCELLED. No guarda: `cancelar_cita` persiste todos los
    cambios en un único UPDATE.
    """
    cita.status = Cita.Estado.CANCELLED
    cita.cancelled_at = ahora


def registrar_cancelacion_tardia(cita: Cita) -> None:
    """Marca la cancelación como tardía para que HU-19 (SmartGuard) la cuente.

    No guarda: va en el mismo UPDATE que la cancelación, así que no puede
    quedar una cita cancelada sin su marca ni una marca sin cancelación.
    """
    cita.late_cancellation = True


def _bloquear_cita(cita_id: int) -> Cita:
    """SELECT ... FOR UPDATE de la cita; debe llamarse dentro de `atomic()`.

    Relee la fila ya con el bloqueo, así que ve lo que confirmaron las
    transacciones que esperaban antes (p. ej. una cancelación concurrente).
    """
    cita = Cita.objects.select_for_update().filter(pk=cita_id).first()
    if cita is None:
        raise CitaNoEncontradaError("La cita no existe.")
    return cita


def _bloquear_barbero(cita: Cita) -> Barbero:
    """SELECT ... FOR UPDATE del barbero de la cita; dentro de `atomic()`.

    Es el mismo recurso que bloquea `crear_cita`, así que reservas nuevas y
    reprogramaciones del mismo barbero se ejecutan de una en una.
    """
    barbero = (
        Barbero.objects.select_for_update()
        .filter(pk=cita.barber_id, barberia_id=cita.barberia_id)
        .first()
    )
    if barbero is None or not barbero.is_active:
        raise RecursoInactivoError("El barbero no esta disponible.")
    return barbero


def cancelar_cita(
    *,
    cita_id: int,
    usuario: AbstractBaseUser,
    ahora: datetime | None = None,
) -> Cita:
    """Cancela la cita del propietario de forma atómica (HU-03).

    La propiedad se comprueba antes de abrir la transacción: un tercero que
    sondea IDs ajenos recibe el rechazo sin llegar a tomar ningún bloqueo.

    Dentro de `transaction.atomic()` se bloquea la fila de la cita con
    SELECT ... FOR UPDATE y se relee, para que dos cancelaciones (doble clic)
    o una cancelación y una reprogramación de la misma cita se ejecuten de una
    en una y cada una decida sobre el estado real. No se bloquea al barbero:
    cancelar solo libera la franja, nunca la ocupa.

    Cancelar siempre se permite al propietario; con la antelación mínima o menos
    se registra como cancelación tardía. `ahora` se toma ya con el bloqueo
    adquirido (o lo inyecta el llamador, para probar el borde exacto).
    """
    cita = obtener_cita_id(cita_id)
    validar_propietario_cita(cita, usuario)

    with transaction.atomic():
        cita = _bloquear_cita(cita_id)
        validar_estado_modificable(cita)
        momento = ahora if ahora is not None else timezone.now()
        validar_cita_no_iniciada(cita, momento)

        liberar_franja_horaria(cita, momento)
        if not tiene_anticipacion_minima(cita.start_at, momento):
            registrar_cancelacion_tardia(cita)

        cita.save(
            update_fields=["status", "cancelled_at", "late_cancellation", "updated_at"]
        )
    return cita


def validar_anticipacion_minima(inicio: datetime, ahora: datetime) -> None:
    """Reprogramar exige MÁS de la antelación mínima sobre la hora original."""
    if not tiene_anticipacion_minima(inicio, ahora):
        raise ReprogramacionTardiaError(MENSAJE_REPROGRAMACION_TARDIA)


def validar_reprogramacion(cita: Cita, nuevo_inicio: datetime, ahora: datetime) -> None:
    """Reglas de la cita y de la hora pedida, con la cita ya bloqueada.

    El orden importa: primero el estado, luego la antelación mínima (medida contra la
    hora ORIGINAL, no la nueva) y al final la validez de la nueva hora.
    """
    validar_estado_modificable(cita)
    validar_anticipacion_minima(cita.start_at, ahora)
    if nuevo_inicio <= ahora:
        raise HorarioInvalidoError("La nueva hora debe ser en el futuro.")
    if nuevo_inicio == cita.start_at:
        raise HorarioInvalidoError("La nueva hora es igual a la actual.")


def validar_franja_en_jornada(
    barbero: Barbero, inicio: datetime, fin: datetime
) -> None:
    """La franja debe caber en la jornada del barbero y no cruzar su descanso.

    Se evalúa en la hora local de la barbería (`ZONA_HORARIA_BARBERIA`), con la
    misma decisión que usa la edición del horario (`apps.barberos.jornada`).
    """
    local_inicio = inicio.astimezone(ZONA_HORARIA_BARBERIA)
    local_fin = fin.astimezone(ZONA_HORARIA_BARBERIA)
    jornada = obtener_jornada_barbero(barbero, local_inicio.date())

    motivo = motivo_franja_fuera_de_jornada(jornada, local_inicio, local_fin)
    if motivo == MOTIVO_EN_DESCANSO:
        raise HorarioInvalidoError("La franja cae en el descanso del barbero.")
    if motivo is not None:
        raise HorarioInvalidoError("La franja está fuera del horario del barbero.")


def reservar_franja_horaria(
    cita: Cita, barbero: Barbero, nuevo_inicio: datetime
) -> None:
    """Mueve la cita a la nueva franja, libre de citas y bloqueos y dentro de jornada.

    La duración sale de la propia cita (no del servicio actual), así que un
    cambio posterior de duración del servicio no altera lo ya reservado. La
    franja anterior queda libre por el mismo cambio de rango: al ser un solo
    UPDATE de la misma fila, el cliente nunca tiene dos franjas ni ninguna.
    No guarda: `reprogramar_cita` persiste.
    """
    nuevo_fin = nuevo_inicio + (cita.end_at - cita.start_at)
    validar_franja_en_jornada(barbero, nuevo_inicio, nuevo_fin)
    if (
        Cita.objects.solapadas(
            barbero, nuevo_inicio, nuevo_fin, excluyendo=cita.pk
        ).exists()
        or BloqueoAgenda.objects.solapados(barbero, nuevo_inicio, nuevo_fin).exists()
    ):
        raise FranjaNoDisponibleError("La franja seleccionada ya no esta disponible.")
    cita.start_at = nuevo_inicio
    cita.end_at = nuevo_fin


def reprogramar_cita(
    *,
    cita_id: int,
    usuario: AbstractBaseUser,
    nuevo_inicio: datetime,
    ahora: datetime | None = None,
) -> Cita:
    """Mueve la cita del propietario a otra hora, con el mismo barbero (HU-03).

    Reprogramar es un UPDATE en sitio de `start_at`/`end_at`: conserva el ID,
    el precio y el estado, y libera la franja vieja y toma la nueva en el mismo
    COMMIT.

    Concurrencia: dentro de `transaction.atomic()` se bloquea primero la CITA
    (serializa contra cancelaciones y otras reprogramaciones de la misma cita)
    y después el BARBERO (serializa contra `crear_cita` y otras
    reprogramaciones que compiten por su agenda). El orden es siempre
    cita -> barbero: `crear_cita` solo toma el barbero y `cancelar_cita` solo
    la cita, así que no puede formarse un ciclo de espera (deadlock). Con
    ambos bloqueos, la disponibilidad se revalida sobre el estado real; el
    ExclusionConstraint queda como respaldo y se traduce al mismo error.
    """
    if timezone.is_naive(nuevo_inicio):
        raise HorarioInvalidoError("La hora de inicio debe incluir zona horaria.")

    cita = obtener_cita_id(cita_id)
    validar_propietario_cita(cita, usuario)

    try:
        with transaction.atomic():
            cita = _bloquear_cita(cita_id)
            barbero = _bloquear_barbero(cita)

            momento = ahora if ahora is not None else timezone.now()
            validar_reprogramacion(cita, nuevo_inicio, momento)
            reservar_franja_horaria(cita, barbero, nuevo_inicio)

            cita.save(update_fields=["start_at", "end_at", "updated_at"])
    except IntegrityError as exc:
        # Se captura fuera del atomic: la transaccion ya hizo ROLLBACK.
        if _restriccion_violada(exc) == RESTRICCION_SOLAPAMIENTO:
            raise FranjaNoDisponibleError(
                "La franja seleccionada ya no esta disponible."
            ) from exc
        raise
    return cita


def obtener_slots_libres(
    *,
    barbero: Barbero,
    fecha: date,
    duracion_minutos: int,
) -> list[dict[str, datetime]]:
    """Calcula los slots libres de un barbero para una fecha determinada.

    Los slots se generan dentro de su horario laboral y se descartan los
    que se solapan con su descanso, citas activas o bloqueos.

    Las citas y bloqueos se consultan para toda la jornada.
    """
    if duracion_minutos not in (30, 60):
        raise ValueError("La duración del slot debe ser de 30 o 60 minutos.")

    if not barbero.is_active:
        return []

    horario = obtener_jornada_barbero(barbero, fecha)

    if horario is None:
        return []

    inicio_jornada = timezone.make_aware(
        datetime.combine(fecha, horario.open_time),
        ZONA_HORARIA_BARBERIA,
    )
    fin_jornada = timezone.make_aware(
        datetime.combine(fecha, horario.close_time),
        ZONA_HORARIA_BARBERIA,
    )

    inicio_descanso = None
    fin_descanso = None

    if horario.break_start is not None:
        inicio_descanso = timezone.make_aware(
            datetime.combine(fecha, horario.break_start),
            ZONA_HORARIA_BARBERIA,
        )
        fin_descanso = inicio_descanso + timedelta(
            minutes=horario.break_duration_minutes
        )

    intervalos_ocupados = list(
        Cita.objects.solapadas(barbero, inicio_jornada, fin_jornada).values_list(
            "start_at", "end_at"
        )
    )
    intervalos_ocupados.extend(
        BloqueoAgenda.objects.solapados(barbero, inicio_jornada, fin_jornada)
        .order_by()
        .values_list("start_at", "end_at")
    )

    slots = []
    duracion = timedelta(minutes=duracion_minutos)
    inicio_slot = inicio_jornada

    while inicio_slot + duracion <= fin_jornada:
        fin_slot = inicio_slot + duracion

        se_solapa_con_descanso = (
            inicio_descanso is not None
            and inicio_slot < fin_descanso
            and fin_slot > inicio_descanso
        )

        se_solapa_con_intervalo = any(
            inicio_slot < fin and fin_slot > inicio
            for inicio, fin in intervalos_ocupados
        )

        if not se_solapa_con_descanso and not se_solapa_con_intervalo:
            slots.append(
                {
                    "start_at": inicio_slot,
                    "end_at": fin_slot,
                }
            )

        inicio_slot += duracion

    return slots


@transaction.atomic
def crear_bloqueo(
    *, barberia: Barberia, barbero_id: int, inicio: datetime, fin: datetime, motivo: str
) -> BloqueoAgenda:
    """Serializa el bloqueo con las reservas usando la misma fila del barbero."""
    try:
        barbero = Barbero.objects.select_for_update().get(
            pk=barbero_id, barberia=barberia, is_active=True
        )
    except Barbero.DoesNotExist as exc:
        raise RecursoInactivoError("El barbero no está disponible.") from exc

    bloqueo = BloqueoAgenda.objects.create(
        barber=barbero, start_at=inicio, end_at=fin, reason=motivo
    )
    _marcar_citas_afectadas(bloqueo)
    return bloqueo


# Citas que un bloqueo puede afectar: las que aun estan por atenderse.
_ESTADOS_AFECTABLES = (Cita.Estado.PENDING, Cita.Estado.CONFIRMED)


def _marcar_citas_afectadas(bloqueo: BloqueoAgenda) -> None:
    """Marca las citas vigentes y futuras del barbero que caen dentro del bloqueo.

    No las cancela ni las mueve: siguen activas y el cliente decide (HU-04). Una
    cita ya marcada por otro bloqueo conserva esa marca, asi no se le avisa dos
    veces. Las que ya empezaron o pasaron no se tocan.
    """
    Cita.objects.filter(
        barber=bloqueo.barber,
        status__in=_ESTADOS_AFECTABLES,
        start_at__lt=bloqueo.end_at,
        end_at__gt=bloqueo.start_at,
        start_at__gt=timezone.now(),
        affected_by_block__isnull=True,
    ).update(affected_by_block=bloqueo)


def _correo_de(cita: Cita) -> str:
    """Correo del cliente con cuenta; vacio para visitantes, que solo dejan celular."""
    return cita.client.email if cita.client_id and cita.client.email else ""


def resumen_citas_afectadas(citas) -> dict:
    """Estado de aviso de las citas afectadas por un bloqueo.

    - notified: el aviso salio bien.
    - without_channel: sin correo (visitantes); el admin debe llamarlos. No son
      "pendientes": el sistema no tiene como avisarles.
    - pending: tienen correo y el aviso aun no sale (fallo del envio).
    """
    citas = list(citas)
    avisadas = [c for c in citas if c.block_notice_sent_at is not None]
    sin_canal = [
        c for c in citas if c.block_notice_sent_at is None and not _correo_de(c)
    ]
    return {
        "total": len(citas),
        "notified": len(avisadas),
        "pending": len(citas) - len(avisadas) - len(sin_canal),
        "without_channel": [
            {
                "id": c.pk,
                "contact_name": c.contact_name,
                "contact_phone": c.contact_phone,
                "start_at": c.start_at.astimezone(ZONA_HORARIA_BARBERIA).isoformat(),
            }
            for c in sin_canal
        ],
    }


def _aviso_de_cita_afectada(cita: Cita) -> tuple[str, str]:
    """Asunto y cuerpo del aviso. No incluye el motivo del bloqueo: es interno."""
    inicio = cita.start_at.astimezone(ZONA_HORARIA_BARBERIA)
    cuando = f"{inicio:%d/%m/%Y} a las {inicio:%H:%M}"
    enlace = f"{settings.FRONTEND_URL}/perfil"
    asunto = f"Tu cita del {inicio:%d/%m/%Y} fue afectada por una ausencia"
    cuerpo = (
        "Hola,\n\n"
        f"Tu cita de {cita.service.name} con {cita.barber.name} el {cuando} se vio "
        "afectada por una ausencia imprevista del barbero.\n\n"
        "Tu cita sigue registrada. Entra a Mis citas para reprogramarla (puedes "
        f"hacerlo hasta {_TEXTO_ANTICIPACION} antes de la hora) o cancelarla: {enlace}\n\n"
        "Lamentamos el inconveniente."
    )
    return asunto, cuerpo


def notificar_citas_afectadas(bloqueo: BloqueoAgenda) -> dict:
    """Avisa por correo a los clientes con cuenta cuyas citas afecto el bloqueo.

    Usa el servicio de HU-05 y debe llamarse DESPUES de confirmar la transaccion
    que creo el bloqueo. Solo guarda `block_notice_sent_at` si el envio salio
    bien; si falla, la cita queda pendiente. Es idempotente: volver a llamarla
    reintenta solo las pendientes y no duplica avisos ya enviados.
    """
    citas = list(
        bloqueo.citas_afectadas.select_related("client", "service", "barber").order_by(
            "start_at"
        )
    )
    for cita in citas:
        correo = _correo_de(cita)
        if cita.block_notice_sent_at is not None or not correo:
            continue
        asunto, cuerpo = _aviso_de_cita_afectada(cita)
        entrega = send_notification_email(recipient=correo, subject=asunto, body=cuerpo)
        if entrega.status == EmailDelivery.Status.SENT:
            cita.block_notice_sent_at = timezone.now()
            cita.save(update_fields=["block_notice_sent_at"])
    return resumen_citas_afectadas(citas)
