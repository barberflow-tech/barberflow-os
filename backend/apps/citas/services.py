"""Casos de uso de citas.

La logica de negocio vive aqui y no en las views: la view (siguiente paso
de HU-02) solo traduce HTTP <-> llamadas a este modulo.
"""

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio

from .models import Cita

RESTRICCION_SOLAPAMIENTO = "cita_sin_solapamiento_por_barbero"


class CitaError(Exception):
    """Error de negocio al gestionar una cita."""


class HorarioInvalidoError(CitaError):
    """La fecha/hora solicitada no es valida (sin zona horaria o en el pasado)."""


class RecursoInactivoError(CitaError):
    """El barbero o el servicio no existe o no esta activo."""


class FranjaNoDisponibleError(CitaError):
    """La franja se solapa con otra cita activa del mismo barbero."""


def crear_cita(
    *,
    cliente,
    barberia: Barberia,
    barbero_id: int,
    servicio_id: int,
    inicio: datetime,
) -> Cita:
    """Crea una cita en estado PENDING de forma atomica (HU-02).

    Bloquea la fila del barbero con SELECT ... FOR UPDATE, de modo que las
    reservas concurrentes de un mismo barbero se ejecutan de una en una, y
    revalida la disponibilidad ya con el bloqueo adquirido. Cualquier
    excepcion dentro del bloque atomico provoca ROLLBACK y libera el bloqueo.

    Barbero y servicio se buscan solo dentro de `barberia` (el tenant del
    usuario): un ID de otra barberia se trata igual que uno inexistente.
    """
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

            # Con el bloqueo adquirido, esta consulta ya ve las citas que
            # confirmaron las transacciones que esperaban antes que esta.
            if Cita.objects.solapadas(barbero, inicio, fin).exists():
                raise FranjaNoDisponibleError(
                    "La franja seleccionada ya no esta disponible."
                )

            return Cita.objects.create(
                barberia=barberia,
                client=cliente,
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
