"""SCRUM-46 / HU-02: E2E del flujo de reserva contra la API.

Recorre el camino real del cliente, sin force_authenticate: se registra, inicia
sesion con JWT, mira el catalogo, consulta la disponibilidad, reserva y
comprueba en la BD que la cita existe y que la franja ya no esta libre.
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

pytestmark = pytest.mark.django_db

REGISTRO = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
SERVICIOS = "/api/v1/services"
DISPONIBILIDAD = "/api/v1/availability"
CITAS = "/api/v1/appointments"

EMAIL = "cliente.e2e@barberflow.test"
CONTRASENA = "Corte.Fade-2026"


@pytest.fixture(autouse=True)
def limpiar_throttle():
    # El limite de reservas sin cuenta se guarda en cache: se limpia por test.
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
            barbero=barbero, weekday=dia, open_time=time(9), close_time=time(12)
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


@pytest.fixture
def servicio_inactivo(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Tinte",
        price=Decimal("50000.00"),
        duration_minutes=30,
        is_active=False,
    )


@pytest.fixture
def fecha():
    return date.today() + timedelta(days=2)


def _slots(api, barbero, fecha):
    respuesta = api.get(
        DISPONIBILIDAD,
        {"barber": barbero.pk, "date": fecha.isoformat(), "slot_duration": 30},
    )
    assert respuesta.status_code == 200
    return [slot["start_at"] for slot in respuesta.json()["available_slots"]]


def _cliente_con_sesion():
    """Registra un cliente nuevo e inicia sesion; devuelve (api, user_id)."""
    api = APIClient()

    registro = api.post(
        REGISTRO, {"email": EMAIL, "password": CONTRASENA}, format="json"
    )
    assert registro.status_code == 201

    login = api.post(LOGIN, {"email": EMAIL, "password": CONTRASENA}, format="json")
    assert login.status_code == 200
    sesion = login.json()
    assert sesion["user"]["role"] == "cliente"

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {sesion['access']}")
    return api, sesion["user"]["id"]


def test_e2e01_flujo_reserva_completo(barbero, servicio, servicio_inactivo, fecha):
    # 1 y 2. Un cliente nuevo se registra e inicia sesion con JWT
    api, user_id = _cliente_con_sesion()

    # 3. Ve el catalogo: solo aparece el servicio activo, con precio y duracion
    catalogo = api.get(SERVICIOS)
    assert catalogo.status_code == 200
    servicios = {s["id"]: s for s in catalogo.json()}
    assert servicio_inactivo.pk not in servicios
    elegido = servicios[servicio.pk]
    assert Decimal(str(elegido["price"])) == Decimal("30000.00")
    assert elegido["duration_minutes"] == 30

    # 4. Consulta la disponibilidad del barbero y toma la primera franja
    libres_antes = _slots(api, barbero, fecha)
    assert len(libres_antes) == 6  # 09:00 a 12:00 en bloques de 30 min
    franja = libres_antes[0]

    # 5. Reserva con servicio, barbero y franja
    reserva = api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": franja},
        format="json",
    )
    assert reserva.status_code == 201
    assert reserva.json()["status"] == "PENDING"

    # 6. En la BD existe una sola cita con ese cliente, barbero, hora y precio
    cita = Cita.objects.get()
    assert cita.client_id == user_id
    assert cita.barber == barbero
    assert cita.service == servicio
    assert cita.start_at.isoformat().replace("+00:00", "Z") in (
        franja,
        franja.replace("+00:00", "Z"),
    )
    assert cita.price == Decimal("30000.00")

    # 7. La franja reservada ya no aparece como libre; las demas siguen
    libres_despues = _slots(api, barbero, fecha)
    assert franja not in libres_despues
    assert libres_despues == libres_antes[1:]


def test_e2e01b_otro_cliente_no_puede_tomar_la_franja_reservada(
    barbero, servicio, fecha
):
    # Dado un cliente que ya reservo la primera franja
    api, _ = _cliente_con_sesion()
    franja = _slots(api, barbero, fecha)[0]
    payload = {"barber": barbero.pk, "service": servicio.pk, "start_at": franja}
    assert api.post(CITAS, payload, format="json").status_code == 201

    # Cuando un visitante intenta reservar la misma franja
    visitante = APIClient().post(
        CITAS,
        {**payload, "contact_name": "Ana Perez", "contact_phone": "3001234567"},
        format="json",
    )

    # Entonces recibe 409 y sigue habiendo una sola cita
    assert visitante.status_code == 409
    assert Cita.objects.count() == 1


def test_e2e01c_visitante_reserva_sin_cuenta_con_nombre_y_celular(
    barbero, servicio, fecha
):
    # Dado un visitante sin cuenta que consulta la disponibilidad
    api = APIClient()
    franja = _slots(api, barbero, fecha)[0]

    # Cuando reserva dejando su nombre y celular
    reserva = api.post(
        CITAS,
        {
            "barber": barbero.pk,
            "service": servicio.pk,
            "start_at": franja,
            "contact_name": "Ana Perez",
            "contact_phone": "3001234567",
        },
        format="json",
    )

    # Entonces la cita queda sin cliente, con el contacto, y la franja se ocupa
    assert reserva.status_code == 201
    cita = Cita.objects.get()
    assert cita.client is None
    assert franja not in _slots(api, barbero, fecha)


def test_e2e02_visitante_sin_token_ni_contacto_no_crea_cita(barbero, servicio, fecha):
    # Dado un visitante sin sesion que no deja nombre ni celular
    api = APIClient()
    franja = _slots(api, barbero, fecha)[0]

    respuesta = api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": franja},
        format="json",
    )

    # Entonces se rechaza y no se crea la cita
    assert respuesta.status_code == 400
    assert set(respuesta.json()) >= {"contact_name", "contact_phone"}
    assert not Cita.objects.exists()


def test_e2e02b_token_alterado_retorna_401_y_no_crea_cita(barbero, servicio, fecha):
    # Dado un cliente cuyo token fue alterado
    api, _ = _cliente_con_sesion()
    franja = _slots(api, barbero, fecha)[0]
    token = api._credentials["HTTP_AUTHORIZATION"]
    api.credentials(HTTP_AUTHORIZATION=token[:-4] + "AAAA")

    respuesta = api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": franja},
        format="json",
    )

    # Entonces no se le trata como visitante: 401 y sin cita
    assert respuesta.status_code == 401
    assert not Cita.objects.exists()


def test_e2e03_reservar_servicio_inactivo_retorna_400(
    barbero, servicio_inactivo, fecha
):
    api, _ = _cliente_con_sesion()
    franja = _slots(api, barbero, fecha)[0]

    respuesta = api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio_inactivo.pk, "start_at": franja},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "service" in respuesta.json()
    assert not Cita.objects.exists()


def test_e2e03b_reservar_servicio_inexistente_retorna_400(barbero, fecha):
    api, _ = _cliente_con_sesion()
    franja = _slots(api, barbero, fecha)[0]

    respuesta = api.post(
        CITAS,
        {"barber": barbero.pk, "service": 999999, "start_at": franja},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "service" in respuesta.json()
    assert not Cita.objects.exists()


def test_e2e04_reservar_en_fecha_pasada_retorna_400(barbero, servicio):
    api, _ = _cliente_con_sesion()
    ayer = (date.today() - timedelta(days=1)).isoformat() + "T10:00:00Z"

    respuesta = api.post(
        CITAS,
        {"barber": barbero.pk, "service": servicio.pk, "start_at": ayer},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "start_at" in respuesta.json()
    assert not Cita.objects.exists()
