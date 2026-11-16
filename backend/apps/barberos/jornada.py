"""Jornada laboral del barbero: fuente unica del horario (HU-08).

Reserva, reprogramacion, disponibilidad y la proteccion de citas al editar el
horario deciden con las mismas funciones de este modulo, asi lo que la
disponibilidad ofrece y lo que la reserva acepta no pueden divergir.

No importa nada de `citas`: los servicios de citas dependen de este modulo y no
al reves.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .models import Barbero, HorarioBarbero

ZONA_HORARIA_BARBERIA = ZoneInfo("America/Bogota")

MOTIVO_DIA_NO_LABORABLE = "dia_no_laborable"
MOTIVO_FUERA_DE_JORNADA = "fuera_de_jornada"
MOTIVO_EN_DESCANSO = "en_descanso"


def obtener_jornada_barbero(barbero: Barbero, fecha: date) -> HorarioBarbero | None:
    """Jornada activa del barbero para el dia de la semana de `fecha`, o None.

    None significa que ese dia no trabaja: sin fila o con la fila desactivada.
    """
    return HorarioBarbero.objects.filter(
        barbero=barbero, weekday=fecha.weekday(), is_active=True
    ).first()


def motivo_franja_fuera_de_jornada(
    jornada: HorarioBarbero | None, local_inicio: datetime, local_fin: datetime
) -> str | None:
    """Por que la franja no cabe en la jornada, o None si cabe.

    Funcion pura: recibe la jornada (guardada o armada en memoria) y la franja
    ya en la hora local de la barberia. Una franja que termina justo al cierre,
    o que empieza justo al terminar el descanso, cabe.
    """
    if jornada is None:
        return MOTIVO_DIA_NO_LABORABLE

    cruza_de_dia = local_inicio.date() != local_fin.date()
    if (
        cruza_de_dia
        or local_inicio.time() < jornada.open_time
        or local_fin.time() > jornada.close_time
    ):
        return MOTIVO_FUERA_DE_JORNADA

    if jornada.break_start is None:
        return None
    se_cruza_con_descanso = (
        local_inicio.time() < jornada.break_end
        and local_fin.time() > jornada.break_start
    )
    return MOTIVO_EN_DESCANSO if se_cruza_con_descanso else None
