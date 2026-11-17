"""Casos de uso del horario semanal del barbero (HU-08 / SCRUM-72).

La logica de negocio vive aqui y no en las views: la view solo traduce HTTP <->
llamadas a este modulo y las excepciones de negocio a respuestas.

Concurrencia: toda escritura abre `transaction.atomic()` y bloquea la fila del
BARBERO con SELECT ... FOR UPDATE. Es el mismo recurso que bloquean
`crear_cita` y `reprogramar_cita`, asi que editar el horario y reservar sobre
ese barbero se ejecutan de una en una y la proteccion de citas (V10) ve el
estado real de la agenda. Editar el horario solo toma ese bloqueo (nunca el de
una cita), por lo que no puede formar un ciclo de espera con la reprogramacion,
que toma cita -> barbero.
"""

from datetime import date, datetime, timedelta
from typing import Any, Iterable

from django.db import transaction
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.citas.models import Cita
from apps.citas.services import ESTADOS_MODIFICABLES
from apps.usuarios.models import Rol, rol_de

from .context import barbero_de
from .jornada import ZONA_HORARIA_BARBERIA, motivo_franja_fuera_de_jornada
from .models import Barbero, HorarioBarbero

DURACIONES_DESCANSO = (30, 60)

MENSAJE_CIERRE = "El cierre debe ser posterior a la apertura."
MENSAJE_DESCANSO_SIN_INICIO = "Configura también la hora de inicio del descanso."
MENSAJE_DESCANSO_SIN_DURACION = "Indica la duración del descanso (30 o 60 minutos)."
MENSAJE_DESCANSO_DURACION = "El descanso debe durar 30 o 60 minutos."
MENSAJE_DESCANSO_FUERA = "El descanso debe estar dentro del horario laboral."
MENSAJE_DIA_REPETIDO = "Este día está repetido en la semana."


class HorarioError(Exception):
    """Error de negocio al gestionar el horario de un barbero."""


class BarberoNoEncontradoError(HorarioError):
    """El barbero no existe o es de otra barberia (se tratan igual)."""


class BarberoInactivoError(HorarioError):
    """El barbero esta inactivo: su horario no se puede modificar."""


class HorarioNoEncontradoError(HorarioError):
    """El barbero no tiene horario ese dia de la semana."""


class HorarioAjenoError(HorarioError):
    """Un barbero intento ver el horario de otro barbero (HU-09)."""


class HorarioInvalidoError(HorarioError):
    """Un dia no cumple las reglas del turno o del descanso."""

    def __init__(self, errores: dict[str, list[str]]):
        super().__init__("El horario no es válido.")
        self.errores = errores


class SemanaInvalidaError(HorarioError):
    """Algun dia de la semana no es valido; `errores` lleva un dict por dia."""

    def __init__(self, errores: list[dict[str, list[str]]]):
        super().__init__("El horario semanal no es válido.")
        self.errores = errores


class CitasAfectadasError(HorarioError):
    """El cambio dejaria citas futuras fuera del horario del barbero."""

    def __init__(self, conflictos: list[dict[str, Any]]):
        super().__init__("El cambio afecta citas futuras.")
        self.conflictos = conflictos


def validar_horario_dia(
    *,
    open_time,
    close_time,
    break_start=None,
    break_duration_minutes: int | None = None,
) -> dict[str, list[str]]:
    """Errores por campo de un dia (vacio si es valido). Reglas V1-V4.

    V1 cierre > apertura. V2 el descanso se configura completo (inicio y
    duracion) o no se configura. V3 dura 30 o 60 minutos. V4 cae dentro del
    turno; se mide con fechas completas, de modo que un descanso que "da la
    vuelta" a medianoche (23:30 + 60 min) no pasa por 00:30.
    """
    errores: dict[str, list[str]] = {}
    if close_time <= open_time:
        errores["close_time"] = [MENSAJE_CIERRE]

    if break_start is None and break_duration_minutes is None:
        return errores
    if break_start is None:
        errores["break_start"] = [MENSAJE_DESCANSO_SIN_INICIO]
        return errores
    if break_duration_minutes is None:
        errores["break_duration_minutes"] = [MENSAJE_DESCANSO_SIN_DURACION]
        return errores
    if break_duration_minutes not in DURACIONES_DESCANSO:
        errores["break_duration_minutes"] = [MENSAJE_DESCANSO_DURACION]
        return errores

    # Con un turno ya invalido no tiene sentido medir el descanso contra el.
    if "close_time" not in errores and not _descanso_cabe_en_turno(
        open_time, close_time, break_start, break_duration_minutes
    ):
        errores["break_start"] = [MENSAJE_DESCANSO_FUERA]
    return errores


def _descanso_cabe_en_turno(open_time, close_time, break_start, minutos: int) -> bool:
    apertura = datetime.combine(date.min, open_time)
    cierre = datetime.combine(date.min, close_time)
    inicio = datetime.combine(date.min, break_start)
    return apertura <= inicio and inicio + timedelta(minutes=minutos) <= cierre


def _campos_horario(datos: dict[str, Any]) -> dict[str, Any]:
    """Los campos del turno y del descanso de un dia, con None si faltan."""
    return {
        "open_time": datos["open_time"],
        "close_time": datos["close_time"],
        "break_start": datos.get("break_start"),
        "break_duration_minutes": datos.get("break_duration_minutes"),
    }


def _obtener_barbero(barbero_id: int, barberia: Barberia) -> Barbero:
    barbero = Barbero.objects.filter(pk=barbero_id, barberia=barberia).first()
    if barbero is None:
        raise BarberoNoEncontradoError("El barbero no existe.")
    return barbero


def _bloquear_barbero(barbero_id: int, barberia: Barberia) -> Barbero:
    """SELECT ... FOR UPDATE del barbero activo; debe llamarse dentro de `atomic()`."""
    barbero = (
        Barbero.objects.select_for_update()
        .filter(pk=barbero_id, barberia=barberia)
        .first()
    )
    if barbero is None:
        raise BarberoNoEncontradoError("El barbero no existe.")
    if not barbero.is_active:
        raise BarberoInactivoError(
            "El barbero está inactivo y no se puede modificar su horario."
        )
    return barbero


def _jornadas_vigentes(barbero: Barbero) -> dict[int, HorarioBarbero]:
    """Dias que hoy trabaja el barbero, por dia de la semana."""
    return {
        horario.weekday: horario
        for horario in HorarioBarbero.objects.filter(barbero=barbero, is_active=True)
    }


def buscar_citas_afectadas(
    barbero: Barbero, jornadas: dict[int, HorarioBarbero], ahora: datetime
) -> list[dict[str, Any]]:
    """Citas futuras del barbero que NO cabrian en `jornadas` (V10).

    `jornadas` es el horario propuesto, por dia de la semana (el dia que falta
    es no laborable). Solo cuentan las citas PENDING o CONFIRMED que aun no
    empiezan: las canceladas y las que ya pasaron no dependen del horario. Usa
    la misma decision que la reserva (`motivo_franja_fuera_de_jornada`) sobre la
    hora local de la barberia, no sobre UTC.
    """
    citas = Cita.objects.filter(
        barber=barbero, status__in=ESTADOS_MODIFICABLES, start_at__gt=ahora
    ).values_list("pk", "start_at", "end_at")

    conflictos = []
    for cita_id, inicio, fin in citas:
        local_inicio = inicio.astimezone(ZONA_HORARIA_BARBERIA)
        local_fin = fin.astimezone(ZONA_HORARIA_BARBERIA)
        motivo = motivo_franja_fuera_de_jornada(
            jornadas.get(local_inicio.weekday()), local_inicio, local_fin
        )
        if motivo is not None:
            conflictos.append({"cita_id": cita_id, "inicio": inicio, "motivo": motivo})
    return conflictos


def _rechazar_si_hay_citas_afectadas(
    barbero: Barbero, jornadas: dict[int, HorarioBarbero], ahora: datetime
) -> None:
    conflictos = buscar_citas_afectadas(barbero, jornadas, ahora)
    if conflictos:
        raise CitasAfectadasError(conflictos)


def validar_horario_propio(*, usuario, barbero_id: int) -> None:
    """Un barbero solo puede ver SU horario; el administrador, el de cualquiera.

    Se decide antes de consultar la barberia: el mismo 403 responde si el
    barbero pedido existe o no, asi que no sirve para sondear IDs ajenos. Una
    cuenta de barbero sin barbero activo vinculado no ve ningun horario.
    """
    if rol_de(usuario) != Rol.BARBERO:
        return
    propio = barbero_de(usuario)
    if propio is None or propio.pk != barbero_id:
        raise HorarioAjenoError("Solo puedes ver tu propio horario.")


def obtener_horario_semanal(
    *, barbero_id: int, barberia: Barberia
) -> tuple[Barbero, list[HorarioBarbero]]:
    """Barbero y sus dias laborables, ordenados de lunes a domingo.

    Lectura sin bloqueo; se permite para un barbero inactivo.
    """
    barbero = _obtener_barbero(barbero_id, barberia)
    dias = list(HorarioBarbero.objects.filter(barbero=barbero, is_active=True))
    return barbero, dias


def reemplazar_horario_semanal(
    *,
    barbero_id: int,
    barberia: Barberia,
    dias: Iterable[dict[str, Any]],
    ahora: datetime | None = None,
) -> tuple[Barbero, list[HorarioBarbero]]:
    """Deja el horario del barbero exactamente igual a `dias`, de forma atomica.

    Los dias omitidos quedan sin trabajo. Es idempotente: repetir la misma
    semana no cambia nada. Orden de las comprobaciones: barbero (404) -> barbero
    activo -> validez de cada dia (todos los errores juntos) -> citas futuras
    (409). Si algo falla no se guarda nada.
    """
    dias = list(dias)
    with transaction.atomic():
        barbero = _bloquear_barbero(barbero_id, barberia)
        nuevos = _validar_semana(dias)

        momento = ahora if ahora is not None else timezone.now()
        _rechazar_si_hay_citas_afectadas(barbero, nuevos, momento)

        HorarioBarbero.objects.filter(barbero=barbero).exclude(
            weekday__in=list(nuevos)
        ).delete()
        for weekday, nuevo in nuevos.items():
            _guardar_dia(barbero, weekday, nuevo)

    return obtener_horario_semanal(barbero_id=barbero.pk, barberia=barberia)


def _validar_semana(dias: list[dict[str, Any]]) -> dict[int, HorarioBarbero]:
    """Valida todos los dias y devuelve el horario propuesto (sin guardar)."""
    errores = []
    repetidos = set()
    for datos in dias:
        errores_dia = validar_horario_dia(**_campos_horario(datos))
        if datos["weekday"] in repetidos:
            errores_dia.setdefault("weekday", []).append(MENSAJE_DIA_REPETIDO)
        repetidos.add(datos["weekday"])
        errores.append(errores_dia)
    if any(errores):
        raise SemanaInvalidaError(errores)

    return {
        datos["weekday"]: HorarioBarbero(
            weekday=datos["weekday"], **_campos_horario(datos)
        )
        for datos in dias
    }


def _guardar_dia(
    barbero: Barbero, weekday: int, propuesto: HorarioBarbero
) -> tuple[HorarioBarbero, bool]:
    """Crea o actualiza el dia (y lo reactiva); devuelve (horario, creado)."""
    return HorarioBarbero.objects.update_or_create(
        barbero=barbero,
        weekday=weekday,
        defaults={
            "open_time": propuesto.open_time,
            "close_time": propuesto.close_time,
            "break_start": propuesto.break_start,
            "break_duration_minutes": propuesto.break_duration_minutes,
            "is_active": True,
        },
    )


def definir_horario_dia(
    *,
    barbero_id: int,
    barberia: Barberia,
    weekday: int,
    datos: dict[str, Any],
    ahora: datetime | None = None,
) -> tuple[HorarioBarbero, bool]:
    """Crea o reemplaza el turno de un dia sin tocar los demas; (horario, creado)."""
    with transaction.atomic():
        barbero = _bloquear_barbero(barbero_id, barberia)

        campos = _campos_horario(datos)
        errores = validar_horario_dia(**campos)
        if errores:
            raise HorarioInvalidoError(errores)

        jornadas = _jornadas_vigentes(barbero)
        propuesto = HorarioBarbero(weekday=weekday, **campos)
        jornadas[weekday] = propuesto
        momento = ahora if ahora is not None else timezone.now()
        _rechazar_si_hay_citas_afectadas(barbero, jornadas, momento)

        return _guardar_dia(barbero, weekday, propuesto)


def eliminar_horario_dia(
    *,
    barbero_id: int,
    barberia: Barberia,
    weekday: int,
    ahora: datetime | None = None,
) -> None:
    """Quita un dia laborable; el barbero deja de ofrecer franjas ese dia."""
    with transaction.atomic():
        barbero = _bloquear_barbero(barbero_id, barberia)

        horario = HorarioBarbero.objects.filter(
            barbero=barbero, weekday=weekday
        ).first()
        if horario is None:
            raise HorarioNoEncontradoError("El barbero no trabaja ese día.")

        jornadas = _jornadas_vigentes(barbero)
        jornadas.pop(weekday, None)
        momento = ahora if ahora is not None else timezone.now()
        _rechazar_si_hay_citas_afectadas(barbero, jornadas, momento)

        horario.delete()
