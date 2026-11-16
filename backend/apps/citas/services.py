"""Casos de uso de citas.

La logica de negocio vive aqui y no en las views: la view (siguiente paso
de HU-02) solo traduce HTTP <-> llamadas a este modulo.
"""

from datetime import date, datetime, timedelta

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

from .models import Cita

RESTRICCION_SOLAPAMIENTO = "cita_sin_solapamiento_por_barbero"

# HU-03: con 12 h o menos de antelacion una cancelacion es tardia (HU-19) y la
# reprogramacion no se permite. "Mas de 12 h" es estricto: 12 h justas no basta.
ANTICIPACION_MINIMA = timedelta(hours=12)
# Solo estas citas se pueden cancelar o reprogramar; el resto ya cerro su ciclo.
ESTADOS_MODIFICABLES = (Cita.Estado.PENDING, Cita.Estado.CONFIRMED)


class CitaError(Exception):
    """Error de negocio al gestionar una cita."""


class HorarioInvalidoError(CitaError):
    """La fecha/hora solicitada no es valida (sin zona horaria o en el pasado)."""


class RecursoInactivoError(CitaError):
    """El barbero o el servicio no existe o no esta activo."""


class FranjaNoDisponibleError(CitaError):
    """La franja se solapa con otra cita activa del mismo barbero."""


class CitaNoEncontradaError(CitaError):
    """La cita no existe."""


class NoEsPropietarioError(CitaError):
    """El usuario no es el propietario de la cita (o la cita no tiene cuenta)."""


class EstadoCitaInvalidoError(CitaError):
    """La cita no se puede modificar: ya terminó su ciclo o ya empezó."""


class ReprogramacionTardiaError(CitaError):
    """Faltan 12 h o menos para la cita: ya no se puede reprogramar."""


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

            # Con el bloqueo adquirido, esta consulta ya ve las citas que
            # confirmaron las transacciones que esperaban antes que esta.
            if Cita.objects.solapadas(barbero, inicio, fin).exists():
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
    """True si faltan MÁS de 12 h para `inicio` (con 12 h justas es False)."""
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

    Cancelar siempre se permite al propietario; con 12 h o menos de antelación
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
    """Reprogramar exige MÁS de 12 h de antelación sobre la hora original."""
    if not tiene_anticipacion_minima(inicio, ahora):
        raise ReprogramacionTardiaError(
            "Solo puedes reprogramar con más de 12 horas de anticipación."
        )


def validar_reprogramacion(cita: Cita, nuevo_inicio: datetime, ahora: datetime) -> None:
    """Reglas de la cita y de la hora pedida, con la cita ya bloqueada.

    El orden importa: primero el estado, luego las 12 h (medidas contra la
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
    """Mueve la cita a la nueva franja, que debe estar libre y dentro de jornada.

    La duración sale de la propia cita (no del servicio actual), así que un
    cambio posterior de duración del servicio no altera lo ya reservado. La
    franja anterior queda libre por el mismo cambio de rango: al ser un solo
    UPDATE de la misma fila, el cliente nunca tiene dos franjas ni ninguna.
    No guarda: `reprogramar_cita` persiste.
    """
    nuevo_fin = nuevo_inicio + (cita.end_at - cita.start_at)
    validar_franja_en_jornada(barbero, nuevo_inicio, nuevo_fin)
    if Cita.objects.solapadas(
        barbero, nuevo_inicio, nuevo_fin, excluyendo=cita.pk
    ).exists():
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
    que se solapan con su descanso o con citas activas.

    La consulta de citas se realiza una sola vez para toda la jornada.
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

    # Una sola consulta obtiene todas las citas activas que se cruzan
    # con la jornada laboral.
    citas_ocupadas = list(
        Cita.objects.activas()
        .filter(
            barber=barbero,
            start_at__lt=fin_jornada,
            end_at__gt=inicio_jornada,
        )
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

        se_solapa_con_cita = any(
            inicio_slot < fin_cita and fin_slot > inicio_cita
            for inicio_cita, fin_cita in citas_ocupadas
        )

        if not se_solapa_con_descanso and not se_solapa_con_cita:
            slots.append(
                {
                    "start_at": inicio_slot,
                    "end_at": fin_slot,
                }
            )

        inicio_slot += duracion

    return slots
