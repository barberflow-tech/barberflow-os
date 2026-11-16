"""Días laborables del barbero en la lista pública (HU-03 / HU-08).

El cliente elige fecha en el asistente de reserva y en el modal de reprogramar.
Para no ofrecerle días en que el barbero no atiende, GET /api/v1/barbers expone
`working_days` (0 lunes a 6 domingo), calculado desde el horario que el
administrador configuró (HU-08).
"""

from datetime import time

import pytest
from rest_framework.test import APIClient

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo

URL = "/api/v1/barbers"

pytestmark = pytest.mark.django_db


@pytest.fixture
def barberia():
    return obtener_barberia_catalogo()


def horario(barbero, dia, *, activo=True):
    return HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=dia,
        open_time=time(9, 0),
        close_time=time(19, 0),
        is_active=activo,
    )


def barbero_de(barberia, nombre):
    return Barbero.objects.create(barberia=barberia, name=nombre)


def dias_de(response, nombre):
    return next(b["working_days"] for b in response.data if b["name"] == nombre)


def test_lista_los_dias_que_el_barbero_atiende_ordenados(barberia):
    thiago = barbero_de(barberia, "Thiago")
    for dia in (4, 0, 2):
        horario(thiago, dia)

    response = APIClient().get(URL)

    assert response.status_code == 200
    assert dias_de(response, "Thiago") == [0, 2, 4]


def test_no_cuenta_los_dias_desactivados(barberia):
    thiago = barbero_de(barberia, "Thiago")
    horario(thiago, 0)
    horario(thiago, 1, activo=False)

    response = APIClient().get(URL)

    assert dias_de(response, "Thiago") == [0]


def test_barbero_sin_horario_no_tiene_dias_laborables(barberia):
    barbero_de(barberia, "Nuevo")

    response = APIClient().get(URL)

    assert dias_de(response, "Nuevo") == []


def test_cada_barbero_trae_solo_sus_propios_dias(barberia):
    thiago = barbero_de(barberia, "Thiago")
    andres = barbero_de(barberia, "Andrés")
    horario(thiago, 0)
    horario(andres, 5)

    response = APIClient().get(URL)

    assert dias_de(response, "Thiago") == [0]
    assert dias_de(response, "Andrés") == [5]


def test_refleja_el_cambio_de_horario_que_hace_el_administrador(barberia):
    thiago = barbero_de(barberia, "Thiago")
    horario(thiago, 0)
    assert dias_de(APIClient().get(URL), "Thiago") == [0]

    HorarioBarbero.objects.filter(barbero=thiago, weekday=0).delete()
    horario(thiago, 3)

    assert dias_de(APIClient().get(URL), "Thiago") == [3]


def test_la_lista_no_hace_una_consulta_por_barbero(
    barberia, django_assert_max_num_queries
):
    for i in range(5):
        barbero = barbero_de(barberia, f"Barbero {i}")
        horario(barbero, 0)

    # Con prefetch el número de consultas no crece con la cantidad de barberos.
    with django_assert_max_num_queries(8):
        APIClient().get(URL)
