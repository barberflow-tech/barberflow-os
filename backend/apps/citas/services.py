"""Casos de uso de citas.

La logica de negocio vive aqui y no en las views: la view (siguiente paso
de HU-02) solo traduce HTTP <-> llamadas a este modulo.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio

from .models import BloqueoAgenda, Cita

RESTRICCION_SOLAPAMIENTO = "cita_sin_solapamiento_por_barbero"
ZONA_HORARIA_BARBERIA = ZoneInfo("America/Bogota")


class CitaError(Exception):
    """Error de negocio al gestionar una cita."""


class HorarioInvalidoError(CitaError):
    """La fecha/hora solicitada no es valida (sin zona horaria o en el pasado)."""


class RecursoInactivoError(CitaError):
    """El barbero o el servicio no existe o no esta activo."""


class FranjaNoDisponibleError(CitaError):
    """La franja se solapa con una cita activa o un bloqueo del barbero."""


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

    horario = HorarioBarbero.objects.filter(
        barbero=barbero,
        weekday=fecha.weekday(),
        is_active=True,
    ).first()

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

    return BloqueoAgenda.objects.create(
        barber=barbero, start_at=inicio, end_at=fin, reason=motivo
    )
