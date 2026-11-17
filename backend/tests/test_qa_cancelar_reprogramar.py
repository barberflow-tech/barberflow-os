"""SCRUM-55 / HU-03: QA de cancelar y reprogramar (regla de antelacion, concurrencia y E2E).

Complementa las pruebas de SCRUM-52 (test_cancelar_cita.py, test_reprogramar_cita.py
y test_concurrencia_reprogramar_cita.py) desde el lado del cliente: todo va por
HTTP con un JWT real, como lo usa el frontend.

La antelacion minima la define CITAS_ANTICIPACION_MINIMA_HORAS (hoy 2 h; el
ticket nacio con 12 h). Las pruebas leen ese valor, asi que siguen validas si
el equipo lo vuelve a cambiar.
"""

import threading
from datetime import datetime, timedelta
from datetime import time as hora_del_dia
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita
from apps.citas.services import ANTICIPACION_MINIMA, ZONA_HORARIA_BARBERIA

pytestmark = pytest.mark.django_db

REGISTRO = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
CITAS = "/api/v1/appointments"
DISPONIBILIDAD = "/api/v1/availability"
CONTRASENA = "Corte.Fade-2026"


def hora_local(dias, hora, minuto=0):
    """Hora de pared en la barberia, `dias` despues de hoy."""
    hoy = timezone.now().astimezone(ZONA_HORARIA_BARBERIA).date()
    return datetime.combine(
        hoy + timedelta(days=dias),
        hora_del_dia(hora, minuto),
        tzinfo=ZONA_HORARIA_BARBERIA,
    )


def reprogramar(api, cita_id, inicio):
    return api.post(
        f"{CITAS}/{cita_id}/reschedule",
        {"start_at": inicio.isoformat()},
        format="json",
    )


def cancelar(api, cita_id):
    return api.post(f"{CITAS}/{cita_id}/cancel")


def franjas_libres(api, barbero, dia):
    respuesta = api.get(
        DISPONIBILIDAD,
        {"barber": barbero.pk, "date": dia.isoformat(), "slot_duration": 30},
    )
    assert respuesta.status_code == 200
    return {
        datetime.fromisoformat(s["start_at"].replace("Z", "+00:00"))
        for s in respuesta.json()["available_slots"]
    }


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def barberia():
    return obtener_barberia_catalogo()


@pytest.fixture
def barbero(barberia):
    barbero = Barbero.objects.create(barberia=barberia, name="Thiago")
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=dia,
            open_time=hora_del_dia(0, 0),
            close_time=hora_del_dia(23, 59),
        )
    return barbero


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("30000.00"),
        duration_minutes=30,
    )


def api_de(usuario):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
    return api


def cita_de(cliente, barbero, servicio, inicio):
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
        price=servicio.price,
        status=Cita.Estado.CONFIRMED,
    )


# --- E2E: reservar, reprogramar y cancelar como lo hace el cliente --------


def test_e2e_reservar_reprogramar_y_cancelar(barbero, servicio):
    # Dado un cliente nuevo que se registra e inicia sesion
    api = APIClient()
    email = "cliente.hu03@barberflow.test"
    assert (
        api.post(
            REGISTRO, {"email": email, "password": CONTRASENA}, format="json"
        ).status_code
        == 201
    )
    login = api.post(LOGIN, {"email": email, "password": CONTRASENA}, format="json")
    assert login.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")

    # Y reserva el pasado manana a las 10:00
    franja_a = hora_local(2, 10)
    franja_b = hora_local(3, 15)
    reserva = api.post(
        CITAS,
        {
            "barber": barbero.pk,
            "service": servicio.pk,
            "start_at": franja_a.isoformat(),
        },
        format="json",
    )
    assert reserva.status_code == 201
    cita_id = reserva.json()["id"]

    # Entonces la ve en "Mis citas" con el limite para reprogramar
    mis_citas = api.get(CITAS).json()
    assert [c["id"] for c in mis_citas] == [cita_id]
    limite = datetime.fromisoformat(
        mis_citas[0]["reschedule_deadline"].replace("Z", "+00:00")
    )
    assert limite == franja_a - ANTICIPACION_MINIMA

    # Cuando la reprograma a otro dia
    respuesta = reprogramar(api, cita_id, franja_b)

    # Entonces se mueve y la franja anterior queda libre de nuevo
    assert respuesta.status_code == 200
    assert franja_a in franjas_libres(api, barbero, franja_a.date())
    assert franja_b not in franjas_libres(api, barbero, franja_b.date())
    cita = Cita.objects.get(pk=cita_id)
    assert cita.start_at == franja_b
    assert cita.price == Decimal("30000.00")

    # Cuando la cancela
    cancelada = cancelar(api, cita_id)

    # Entonces queda cancelada, sale de "Mis citas" y libera la franja
    assert cancelada.status_code == 200
    assert cancelada.json()["status"] == "CANCELLED"
    assert cancelada.json()["late_cancellation"] is False
    assert api.get(CITAS).json() == []
    assert franja_b in franjas_libres(api, barbero, franja_b.date())


# --- Limite de antelacion (criterios de aceptacion 1 y 2) ----------------


@pytest.mark.parametrize(
    "margen,esperado",
    [
        (timedelta(minutes=1), 200),
        (timedelta(hours=1), 200),
        (timedelta(minutes=-1), 400),
        (timedelta(hours=-1), 400),
    ],
    ids=["1-min-antes-del-limite", "1-h-antes", "1-min-tarde", "1-h-tarde"],
)
def test_reprogramar_respeta_el_limite_de_antelacion(
    make_user, barbero, servicio, margen, esperado
):
    # Dado una cita que empieza justo alrededor del limite de antelacion
    cliente = make_user("cliente")
    inicio = timezone.now() + ANTICIPACION_MINIMA + margen
    cita = cita_de(cliente, barbero, servicio, inicio)

    # Cuando el cliente la reprograma a otro dia
    respuesta = reprogramar(api_de(cliente), cita.pk, hora_local(4, 11))

    # Entonces pasa con mas antelacion de la minima y falla con 400 con menos
    assert respuesta.status_code == esperado
    cita.refresh_from_db()
    if esperado == 400:
        assert cita.start_at == inicio


@pytest.mark.parametrize(
    "margen,tardia",
    [(timedelta(minutes=1), False), (timedelta(minutes=-1), True)],
    ids=["a-tiempo", "tardia"],
)
def test_cancelar_marca_tardia_solo_dentro_del_limite(
    make_user, barbero, servicio, margen, tardia
):
    # Cancelar siempre se permite; dentro del limite queda marcada como tardia
    cliente = make_user("cliente")
    cita = cita_de(
        cliente, barbero, servicio, timezone.now() + ANTICIPACION_MINIMA + margen
    )

    respuesta = cancelar(api_de(cliente), cita.pk)

    assert respuesta.status_code == 200
    assert respuesta.json()["late_cancellation"] is tardia


def test_no_se_puede_reprogramar_ni_cancelar_la_cita_de_otro(
    make_user, barbero, servicio
):
    duena = make_user("cliente", email="duena@barberflow.test")
    otro = make_user("cliente", email="otro@barberflow.test")
    cita = cita_de(duena, barbero, servicio, hora_local(2, 10))
    api_otro = api_de(otro)

    assert reprogramar(api_otro, cita.pk, hora_local(3, 10)).status_code == 403
    assert cancelar(api_otro, cita.pk).status_code == 403
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.CONFIRMED
    assert cita.start_at == hora_local(2, 10)


def test_sin_sesion_no_se_puede_reprogramar_ni_cancelar(make_user, barbero, servicio):
    cita = cita_de(make_user("cliente"), barbero, servicio, hora_local(2, 10))

    assert reprogramar(APIClient(), cita.pk, hora_local(3, 10)).status_code == 401
    assert cancelar(APIClient(), cita.pk).status_code == 401


# --- Concurrencia (criterio de aceptacion 3) ------------------------------


def _en_paralelo(acciones):
    """Lanza las acciones a la vez y devuelve sus codigos HTTP en orden."""
    barrera = threading.Barrier(len(acciones))
    codigos = [None] * len(acciones)

    def correr(indice, accion):
        try:
            barrera.wait()
            codigos[indice] = accion().status_code
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=correr, args=(i, accion))
        for i, accion in enumerate(acciones)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(20)
    return codigos


@pytest.mark.django_db(transaction=True)
def test_dos_clientes_reprograman_a_la_misma_franja_a_la_vez(
    make_user, barbero, servicio
):
    # Dado dos clientes con citas distintas
    ana = make_user("cliente", email="ana@barberflow.test")
    luis = make_user("cliente", email="luis@barberflow.test")
    cita_ana = cita_de(ana, barbero, servicio, hora_local(2, 9))
    cita_luis = cita_de(luis, barbero, servicio, hora_local(2, 14))
    destino = hora_local(3, 16)
    api_ana, api_luis = api_de(ana), api_de(luis)

    # Cuando los dos piden la misma franja nueva al mismo tiempo
    codigos = _en_paralelo(
        [
            lambda: reprogramar(api_ana, cita_ana.pk, destino),
            lambda: reprogramar(api_luis, cita_luis.pk, destino),
        ]
    )

    # Entonces uno la obtiene y el otro recibe 409, sin citas cruzadas
    assert sorted(codigos) == [200, 409]
    assert Cita.objects.filter(start_at=destino).count() == 1


@pytest.mark.django_db(transaction=True)
def test_cinco_clientes_reprograman_a_la_misma_franja_solo_uno_gana(
    make_user, barbero, servicio
):
    clientes = [make_user("cliente", email=f"c{i}@barberflow.test") for i in range(5)]
    citas = [
        cita_de(c, barbero, servicio, hora_local(2, 8 + i))
        for i, c in enumerate(clientes)
    ]
    destino = hora_local(3, 16)
    apis = [api_de(c) for c in clientes]

    codigos = _en_paralelo(
        [
            (lambda api=api, cita=cita: reprogramar(api, cita.pk, destino))
            for api, cita in zip(apis, citas)
        ]
    )

    assert sorted(codigos) == [200] + [409] * 4
    assert Cita.objects.filter(start_at=destino).count() == 1


@pytest.mark.django_db(transaction=True)
def test_reprogramar_y_un_visitante_reservando_la_misma_franja(
    make_user, barbero, servicio
):
    # Un cliente reprograma a una franja mientras un visitante la reserva
    cliente = make_user("cliente")
    cita = cita_de(cliente, barbero, servicio, hora_local(2, 9))
    destino = hora_local(3, 16)
    api_cliente = api_de(cliente)
    visitante = APIClient()

    codigos = _en_paralelo(
        [
            lambda: reprogramar(api_cliente, cita.pk, destino),
            lambda: visitante.post(
                CITAS,
                {
                    "barber": barbero.pk,
                    "service": servicio.pk,
                    "start_at": destino.isoformat(),
                    "contact_name": "Ana Perez",
                    "contact_phone": "3001234567",
                },
                format="json",
            ),
        ]
    )

    # Solo uno se queda con la franja
    assert codigos.count(409) == 1
    assert Cita.objects.filter(start_at=destino).count() == 1
