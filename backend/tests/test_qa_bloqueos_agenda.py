"""SCRUM-61 / HU-04: QA de bloqueos de agenda, citas afectadas y permisos.

Complementa test_bloqueos_agenda.py y test_bloqueo_citas_afectadas.py (SCRUM-58
y SCRUM-60) con el punto de vista del cliente: reservas con cuenta dentro y en
el borde del bloqueo, bloqueos parciales y solapados, el flujo completo de una
cita afectada, permisos con payload valido y un bloqueo que llega mientras un
cliente reserva. Todo por HTTP con JWT real; el correo usa el buzon de prueba.
"""

import threading
from datetime import datetime, timedelta
from datetime import time as hora_del_dia
from decimal import Decimal

import pytest
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import BloqueoAgenda, Cita
from apps.citas.services import ZONA_HORARIA_BARBERIA

pytestmark = pytest.mark.django_db

BLOQUEOS = "/api/v1/blocks"
CITAS = "/api/v1/appointments"
DISPONIBILIDAD = "/api/v1/availability"


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


def api_de(usuario):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
    return api


@pytest.fixture
def dia():
    """Pasado manana, en la zona de la barberia."""
    return timezone.localdate(timezone=ZONA_HORARIA_BARBERIA) + timedelta(days=2)


def a_las(dia, hora, minuto=0):
    return datetime.combine(
        dia, hora_del_dia(hora, minuto), tzinfo=ZONA_HORARIA_BARBERIA
    )


@pytest.fixture
def agenda(make_user, dia):
    """Barberia del catalogo con admin, dos barberos (9:00-13:00) y un servicio."""
    barberia = obtener_barberia_catalogo()
    admin = make_user("admin")
    Membresia.objects.create(user=admin, barberia=barberia)
    barberos = []
    for nombre in ("Ana", "Beto"):
        barbero = Barbero.objects.create(barberia=barberia, name=nombre)
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=dia.weekday(),
            open_time=hora_del_dia(9),
            close_time=hora_del_dia(13),
        )
        barberos.append(barbero)
    servicio = Servicio.objects.create(
        barberia=barberia,
        name="Corte",
        price=Decimal("30000.00"),
        duration_minutes=30,
    )
    return {
        "admin": api_de(admin),
        "ana": barberos[0],
        "beto": barberos[1],
        "servicio": servicio,
    }


def bloquear(api, barbero, inicio, fin, motivo="Incapacidad"):
    return api.post(
        BLOQUEOS,
        {
            "barber": barbero.pk,
            "start_at": inicio.isoformat(),
            "end_at": fin.isoformat(),
            "reason": motivo,
        },
        format="json",
    )


def reservar(api, barbero, servicio, inicio):
    return api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": inicio.isoformat()},
        format="json",
    )


def libres(barbero, dia):
    respuesta = APIClient().get(
        DISPONIBILIDAD,
        {"barber": barbero.pk, "date": dia.isoformat(), "slot_duration": 30},
    )
    assert respuesta.status_code == 200
    return [
        datetime.fromisoformat(s["start_at"].replace("Z", "+00:00"))
        .astimezone(ZONA_HORARIA_BARBERIA)
        .time()
        .strftime("%H:%M")
        for s in respuesta.json()["available_slots"]
    ]


# --- Criterio 1: el bloqueo deshabilita la reserva -----------------------


def test_cliente_con_cuenta_no_puede_reservar_dentro_del_bloqueo(
    agenda, make_user, dia
):
    # Dado un bloqueo de 10:00 a 11:00
    assert bloquear(
        agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11)
    ).status_code == (201)
    cliente = api_de(make_user("cliente"))

    # Cuando un cliente con sesion intenta reservar a las 10:30
    respuesta = reservar(cliente, agenda["ana"], agenda["servicio"], a_las(dia, 10, 30))

    # Entonces recibe 409 y no se crea la cita
    assert respuesta.status_code == 409
    assert not Cita.objects.exists()


@pytest.mark.parametrize(
    "hora,minuto,esperado",
    [
        (9, 30, 201),  # termina justo cuando empieza el bloqueo
        (9, 45, 409),  # se mete 15 minutos en el bloqueo
        (10, 45, 409),  # empieza dentro y termina despues
        (11, 0, 201),  # empieza justo cuando termina el bloqueo
    ],
    ids=["termina-en-el-borde", "entra-15-min", "sale-15-min", "empieza-en-el-borde"],
)
def test_bordes_del_bloqueo_al_reservar(agenda, make_user, dia, hora, minuto, esperado):
    bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11))
    cliente = api_de(make_user("cliente"))

    respuesta = reservar(
        cliente, agenda["ana"], agenda["servicio"], a_las(dia, hora, minuto)
    )

    assert respuesta.status_code == esperado


def test_bloqueo_parcial_solo_quita_las_franjas_que_toca(agenda, dia):
    # Un bloqueo de 10:10 a 10:20 deja sin servicio solo la franja de 10:00
    assert libres(agenda["ana"], dia) == [
        "09:00",
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
        "12:00",
        "12:30",
    ]

    bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10, 10), a_las(dia, 10, 20))

    assert "10:00" not in libres(agenda["ana"], dia)
    assert len(libres(agenda["ana"], dia)) == 7


def test_bloqueos_solapados_suman_y_al_borrar_uno_queda_el_otro(agenda, dia):
    # Dado dos bloqueos que se cruzan: 10:00-11:00 y 10:30-12:00
    primero = bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11))
    bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10, 30), a_las(dia, 12))
    assert libres(agenda["ana"], dia) == ["09:00", "09:30", "12:00", "12:30"]

    # Cuando se borra el primero, el hueco del segundo sigue bloqueado
    assert (
        agenda["admin"].delete(f"{BLOQUEOS}/{primero.json()['id']}").status_code == 204
    )
    assert libres(agenda["ana"], dia) == [
        "09:00",
        "09:30",
        "10:00",
        "12:00",
        "12:30",
    ]


def test_bloqueo_de_un_barbero_no_afecta_a_otro(agenda, make_user, dia):
    bloquear(agenda["admin"], agenda["ana"], a_las(dia, 9), a_las(dia, 13))
    cliente = api_de(make_user("cliente"))

    assert libres(agenda["ana"], dia) == []
    assert len(libres(agenda["beto"], dia)) == 8
    assert (
        reservar(
            cliente, agenda["beto"], agenda["servicio"], a_las(dia, 10)
        ).status_code
        == 201
    )


def test_borrar_el_bloqueo_vuelve_a_habilitar_la_reserva(agenda, make_user, dia):
    bloqueo = bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11))
    cliente = api_de(make_user("cliente"))
    assert (
        reservar(cliente, agenda["ana"], agenda["servicio"], a_las(dia, 10)).status_code
        == 409
    )

    agenda["admin"].delete(f"{BLOQUEOS}/{bloqueo.json()['id']}")

    assert (
        reservar(cliente, agenda["ana"], agenda["servicio"], a_las(dia, 10)).status_code
        == 201
    )


# --- Citas afectadas: flujo completo ------------------------------------


def test_e2e_cita_afectada_se_marca_y_el_cliente_recibe_aviso(agenda, make_user, dia):
    # Dado un cliente con una cita a las 10:00
    cliente = make_user("cliente", email="cliente.afectado@barberflow.test")
    api_cliente = api_de(cliente)
    reserva = reservar(api_cliente, agenda["ana"], agenda["servicio"], a_las(dia, 10))
    assert reserva.status_code == 201

    # Cuando el admin bloquea la manana del barbero
    respuesta = bloquear(
        agenda["admin"], agenda["ana"], a_las(dia, 9), a_las(dia, 12), "Cita medica"
    )

    # Entonces el bloqueo informa una cita afectada y ya avisada
    assert respuesta.status_code == 201
    afectadas = respuesta.json()["affected_appointments"]
    assert afectadas["total"] == 1
    assert afectadas["notified"] == 1
    assert afectadas["pending"] == 0

    # Y la cita sigue activa, marcada, y el cliente recibio un solo correo
    cita = Cita.objects.get(pk=reserva.json()["id"])
    assert cita.status in (Cita.Estado.PENDING, Cita.Estado.CONFIRMED)
    assert cita.affected_by_block_id == respuesta.json()["id"]
    assert [m.to for m in mail.outbox] == [[cliente.email]]
    assert "Cita medica" not in mail.outbox[0].body

    # Y el cliente puede moverla a otro barbero libre
    assert (
        reservar(
            api_cliente, agenda["beto"], agenda["servicio"], a_las(dia, 10)
        ).status_code
        == 201
    )


# --- Criterio 2: permisos -------------------------------------------------


@pytest.mark.parametrize("rol", ["cliente", "barbero"])
def test_cliente_o_barbero_no_pueden_crear_bloqueos_con_payload_valido(
    agenda, make_user, dia, rol
):
    # Con un payload correcto, para que el 403 no venga de una validacion
    usuario = make_user(rol)
    Membresia.objects.create(user=usuario, barberia=obtener_barberia_catalogo())

    respuesta = bloquear(api_de(usuario), agenda["ana"], a_las(dia, 10), a_las(dia, 11))

    assert respuesta.status_code == 403
    assert not BloqueoAgenda.objects.exists()


@pytest.mark.parametrize("rol", ["cliente", "barbero"])
def test_cliente_o_barbero_no_pueden_borrar_un_bloqueo(agenda, make_user, dia, rol):
    bloqueo = bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11))

    respuesta = api_de(make_user(rol)).delete(f"{BLOQUEOS}/{bloqueo.json()['id']}")

    assert respuesta.status_code == 403
    assert BloqueoAgenda.objects.count() == 1


def test_sin_sesion_no_se_puede_bloquear(agenda, dia):
    respuesta = bloquear(APIClient(), agenda["ana"], a_las(dia, 10), a_las(dia, 11))

    assert respuesta.status_code == 401
    assert not BloqueoAgenda.objects.exists()


def test_admin_de_otra_barberia_no_bloquea_ni_borra_aqui(agenda, make_user, dia):
    otro_admin = make_user("admin", email="admin.otra@barberflow.test")
    Membresia.objects.create(
        user=otro_admin, barberia=Barberia.objects.create(name="Otra barberia")
    )
    api_otro = api_de(otro_admin)
    bloqueo = bloquear(agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11))

    # No puede bloquear un barbero ajeno ni borrar un bloqueo ajeno
    assert (
        bloquear(api_otro, agenda["ana"], a_las(dia, 11), a_las(dia, 12)).status_code
        == 400
    )
    assert api_otro.delete(f"{BLOQUEOS}/{bloqueo.json()['id']}").status_code == 404
    assert BloqueoAgenda.objects.count() == 1


# --- Concurrencia: bloqueo y reserva al mismo tiempo ---------------------


@pytest.mark.django_db(transaction=True)
def test_bloqueo_y_reserva_simultaneos_no_dejan_una_cita_sin_marcar(
    agenda, make_user, dia
):
    # Dado un admin que bloquea las 10:00 mientras un cliente reserva esa franja
    cliente = make_user("cliente", email="carrera@barberflow.test")
    api_cliente = api_de(cliente)
    barrera = threading.Barrier(2)
    codigos = {}

    def correr(nombre, accion):
        try:
            barrera.wait()
            codigos[nombre] = accion().status_code
        finally:
            connection.close()

    hilos = [
        threading.Thread(
            target=correr,
            args=(
                "bloqueo",
                lambda: bloquear(
                    agenda["admin"], agenda["ana"], a_las(dia, 10), a_las(dia, 11)
                ),
            ),
        ),
        threading.Thread(
            target=correr,
            args=(
                "reserva",
                lambda: reservar(
                    api_cliente, agenda["ana"], agenda["servicio"], a_las(dia, 10)
                ),
            ),
        ),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(20)

    # Entonces el bloqueo siempre se crea, y si la reserva gano la carrera
    # su cita queda marcada como afectada; si perdio, recibio 409
    assert codigos["bloqueo"] == 201
    assert codigos["reserva"] in (201, 409)
    citas = Cita.objects.filter(barber=agenda["ana"])
    if codigos["reserva"] == 201:
        assert citas.get().affected_by_block is not None
    else:
        assert not citas.exists()
