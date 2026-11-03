from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita
from apps.citas.services import obtener_slots_libres

BOGOTA = ZoneInfo("America/Bogota")
URL = "/api/v1/availability/"


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def cliente(django_user_model, barberia):
    usuario = django_user_model.objects.create_user(
        username="cliente_disponibilidad",
        password="x",
    )
    Membresia.objects.create(user=usuario, barberia=barberia)
    return usuario


@pytest.fixture
def api(cliente):
    client = APIClient()
    client.force_authenticate(user=cliente)
    return client


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Juan")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte clasico",
        price=25000,
        duration_minutes=30,
    )


@pytest.fixture
def fecha():
    return timezone.localdate() + timedelta(days=3)


@pytest.fixture
def horario(barbero, fecha):
    return HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=fecha.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
    )


def fecha_hora(fecha, hora):
    return timezone.make_aware(
        datetime.combine(fecha, hora),
        BOGOTA,
    )


def crear_cita(barbero, servicio, fecha, inicio, fin, estado=Cita.Estado.PENDING):
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=barbero.barberia.membresias.first().user,
        barber=barbero,
        service=servicio,
        start_at=fecha_hora(fecha, inicio),
        end_at=fecha_hora(fecha, fin),
        status=estado,
        price=servicio.price,
    )


@pytest.mark.django_db
def test_genera_slots_de_30_minutos_dentro_del_horario(barbero, horario, fecha):
    # Dado un barbero que trabaja de 09:00 a 17:00
    # Cuando se consultan slots de 30 minutos
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=30,
    )

    # Entonces genera 16 slots, desde las 09:00 hasta las 16:30
    assert len(slots) == 16
    assert slots[0]["start_at"] == fecha_hora(fecha, time(9, 0))
    assert slots[-1]["start_at"] == fecha_hora(fecha, time(16, 30))
    assert slots[-1]["end_at"] == fecha_hora(fecha, time(17, 0))


@pytest.mark.django_db
def test_excluye_slots_que_se_solapan_con_una_cita(
    barbero, horario, servicio, cliente, fecha
):
    # Dado un barbero con horario de 09:00 a 17:00 y una cita de 10:00 a 11:00
    crear_cita(barbero, servicio, fecha, time(10, 0), time(11, 0))

    # Cuando se consultan slots de 30 minutos
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=30,
    )
    horas = {slot["start_at"].time() for slot in slots}

    # Entonces no aparecen las franjas 10:00 ni 10:30
    assert time(10, 0) not in horas
    assert time(10, 30) not in horas
    assert len(slots) == 14


@pytest.mark.django_db
def test_excluye_slots_que_se_solapan_con_el_descanso(barbero, fecha):
    # Dado un descanso de 13:00 a 13:30
    HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=fecha.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
        break_start=time(13, 0),
        break_duration_minutes=30,
    )

    # Cuando se consultan slots de 30 minutos
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=30,
    )
    horas = {slot["start_at"].time() for slot in slots}

    # Entonces no aparece el slot de las 13:00
    assert time(13, 0) not in horas
    assert len(slots) == 15


@pytest.mark.django_db
def test_slot_de_60_minutos_no_puede_cruzar_un_descanso_de_30(barbero, fecha):
    # Dado un descanso de 13:00 a 13:30
    HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=fecha.weekday(),
        open_time=time(9, 0),
        close_time=time(17, 0),
        break_start=time(13, 0),
        break_duration_minutes=30,
    )

    # Cuando se consultan slots de 60 minutos
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=60,
    )
    horas = {slot["start_at"].time() for slot in slots}

    # Entonces no ofrece slots que crucen el descanso
    assert time(12, 0) in horas
    assert time(13, 0) not in horas
    assert time(14, 0) in horas


@pytest.mark.django_db
def test_cita_cancelada_no_bloquea_disponibilidad(
    barbero, horario, servicio, cliente, fecha
):
    # Dado que existe una cita cancelada de 10:00 a 11:00
    crear_cita(
        barbero,
        servicio,
        fecha,
        time(10, 0),
        time(11, 0),
        estado=Cita.Estado.CANCELLED,
    )

    # Cuando se consultan slots de 30 minutos
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=30,
    )
    horas = {slot["start_at"].time() for slot in slots}

    # Entonces las franjas vuelven a estar disponibles
    assert time(10, 0) in horas
    assert time(10, 30) in horas


@pytest.mark.django_db
def test_no_genera_slots_si_el_barbero_no_trabaja_ese_dia(barbero, fecha):
    # Dado que el barbero no tiene horario configurado para ese día
    # Cuando se consulta su disponibilidad
    slots = obtener_slots_libres(
        barbero=barbero,
        fecha=fecha,
        duracion_minutos=30,
    )

    # Entonces no se ofrecen slots
    assert slots == []


@pytest.mark.django_db
def test_rechaza_duraciones_distintas_de_30_y_60(barbero, horario, fecha):
    # Cuando se solicita una duración no soportada
    # Entonces el servicio rechaza el valor
    with pytest.raises(ValueError):
        obtener_slots_libres(
            barbero=barbero,
            fecha=fecha,
            duracion_minutos=45,
        )


@pytest.mark.django_db
def test_endpoint_retorna_disponibilidad(api, barbero, horario, fecha):
    # Dado un usuario autenticado de la barbería del barbero
    # Cuando consulta la disponibilidad
    response = api.get(
        URL,
        {
            "barber": barbero.pk,
            "date": fecha.isoformat(),
            "slot_duration": 30,
        },
    )

    # Entonces recibe los slots disponibles
    assert response.status_code == 200
    assert response.data["barber"] == barbero.pk
    assert response.data["date"] == fecha.isoformat()
    assert response.data["slot_duration"] == 30
    assert len(response.data["available_slots"]) == 16


@pytest.mark.django_db
def test_endpoint_no_expone_barberos_de_otra_barberia(api, otra_barberia, fecha):
    # Dado un barbero perteneciente a otra barbería
    barbero_ajeno = Barbero.objects.create(
        barberia=otra_barberia,
        name="Pedro",
    )

    # Cuando el usuario intenta consultar su disponibilidad
    response = api.get(
        URL,
        {
            "barber": barbero_ajeno.pk,
            "date": fecha.isoformat(),
            "slot_duration": 30,
        },
    )

    # Entonces el recurso se trata como inexistente
    assert response.status_code == 404


@pytest.mark.django_db
def test_endpoint_exige_autenticacion(barbero, fecha):
    # Cuando un usuario no autenticado consulta disponibilidad
    response = APIClient().get(
        URL,
        {
            "barber": barbero.pk,
            "date": fecha.isoformat(),
            "slot_duration": 30,
        },
    )

    # Entonces la API exige autenticación
    assert response.status_code == 401
