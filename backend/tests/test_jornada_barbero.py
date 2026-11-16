"""Jornada del barbero: fuente unica del horario (HU-08 / SCRUM-72).

`motivo_franja_fuera_de_jornada` es una funcion pura: decide si una franja cabe
en una jornada sin consultar la base. La usan la reserva, la reprogramacion y
la proteccion de citas al editar el horario, para que no puedan divergir.
"""

from datetime import date, datetime, time

import pytest

from apps.barberias.models import Barberia
from apps.barberos.jornada import (
    MOTIVO_DIA_NO_LABORABLE,
    MOTIVO_EN_DESCANSO,
    MOTIVO_FUERA_DE_JORNADA,
    ZONA_HORARIA_BARBERIA,
    motivo_franja_fuera_de_jornada,
    obtener_jornada_barbero,
)
from apps.barberos.models import Barbero, HorarioBarbero

DIA = date(2026, 12, 7)  # un lunes


def local(hora: int, minuto: int = 0, dia: date = DIA) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=ZONA_HORARIA_BARBERIA)


@pytest.fixture
def jornada() -> HorarioBarbero:
    """09:00-17:00 con descanso de 13:00 a 14:00 (sin guardar en la base)."""
    return HorarioBarbero(
        weekday=DIA.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
        break_start=time(13, 0),
        break_duration_minutes=60,
    )


def test_franja_dentro_de_la_jornada_no_tiene_motivo(jornada):
    assert motivo_franja_fuera_de_jornada(jornada, local(10), local(10, 30)) is None


def test_franja_que_termina_justo_al_cierre_cabe(jornada):
    assert motivo_franja_fuera_de_jornada(jornada, local(16, 30), local(17)) is None


def test_franja_que_empieza_justo_a_la_apertura_cabe(jornada):
    assert motivo_franja_fuera_de_jornada(jornada, local(9), local(9, 30)) is None


def test_franja_que_pasa_del_cierre_esta_fuera_de_jornada(jornada):
    motivo = motivo_franja_fuera_de_jornada(jornada, local(16, 30), local(17, 10))
    assert motivo == MOTIVO_FUERA_DE_JORNADA


def test_franja_antes_de_la_apertura_esta_fuera_de_jornada(jornada):
    motivo = motivo_franja_fuera_de_jornada(jornada, local(8, 30), local(9, 10))
    assert motivo == MOTIVO_FUERA_DE_JORNADA


def test_franja_que_cruza_la_medianoche_esta_fuera_de_jornada(jornada):
    inicio = local(16, 30)
    fin = datetime.combine(date(2026, 12, 8), time(0, 30), tzinfo=inicio.tzinfo)
    assert (
        motivo_franja_fuera_de_jornada(jornada, inicio, fin) == MOTIVO_FUERA_DE_JORNADA
    )


def test_franja_que_cruza_el_descanso_cae_en_descanso(jornada):
    motivo = motivo_franja_fuera_de_jornada(jornada, local(12, 30), local(13, 30))
    assert motivo == MOTIVO_EN_DESCANSO


@pytest.mark.parametrize(
    "inicio, fin",
    [
        (local(12), local(13)),  # termina justo cuando empieza el descanso
        (local(14), local(14, 30)),  # empieza justo cuando termina el descanso
    ],
)
def test_franja_pegada_al_descanso_cabe(jornada, inicio, fin):
    assert motivo_franja_fuera_de_jornada(jornada, inicio, fin) is None


def test_sin_jornada_el_dia_no_es_laborable():
    motivo = motivo_franja_fuera_de_jornada(None, local(10), local(10, 30))
    assert motivo == MOTIVO_DIA_NO_LABORABLE


def test_jornada_sin_descanso_no_tiene_motivo_de_descanso():
    sin_descanso = HorarioBarbero(
        weekday=DIA.weekday(), open_time=time(9, 0), close_time=time(17, 0)
    )
    assert motivo_franja_fuera_de_jornada(sin_descanso, local(13), local(14)) is None


@pytest.mark.django_db
def test_obtener_jornada_barbero_devuelve_el_horario_activo_del_dia():
    barbero = Barbero.objects.create(
        barberia=Barberia.objects.create(name="Centro"), name="Juan"
    )
    horario = HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=DIA.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
    )
    assert obtener_jornada_barbero(barbero, DIA) == horario


@pytest.mark.django_db
def test_obtener_jornada_barbero_ignora_dia_sin_horario_o_inactivo():
    barbero = Barbero.objects.create(
        barberia=Barberia.objects.create(name="Centro"), name="Juan"
    )
    HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=DIA.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
        is_active=False,
    )
    assert obtener_jornada_barbero(barbero, DIA) is None  # inactivo
    assert obtener_jornada_barbero(barbero, date(2026, 12, 8)) is None  # sin fila
