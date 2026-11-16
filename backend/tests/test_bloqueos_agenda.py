from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.services import ZONA_HORARIA_BARBERIA

pytestmark = pytest.mark.django_db

BLOCKS = "/api/v1/blocks"


@pytest.fixture
def agenda(admin_user):
    barberia = obtener_barberia_catalogo()
    Membresia.objects.create(user=admin_user, barberia=barberia)
    barbero = Barbero.objects.create(barberia=barberia, name="Ana")
    servicio = Servicio.objects.create(
        barberia=barberia, name="Corte", duration_minutes=30, price=25000
    )
    dia = timezone.localdate(timezone=ZONA_HORARIA_BARBERIA) + timedelta(days=2)
    HorarioBarbero.objects.create(
        barbero=barbero, weekday=dia.weekday(), open_time=time(9), close_time=time(12)
    )
    inicio = datetime.combine(dia, time.min, tzinfo=ZONA_HORARIA_BARBERIA)
    return barbero, servicio, inicio


@pytest.fixture
def admin_api(admin_user, login, api_client):
    respuesta = login(admin_user.email)
    assert respuesta.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return api_client


def _payload(barbero, inicio, fin):
    return {
        "barber": barbero.pk,
        "start_at": inicio.isoformat(),
        "end_at": fin.isoformat(),
        "reason": "Incapacidad",
    }


def _disponibilidad(barbero, inicio):
    respuesta = APIClient().get(
        "/api/v1/availability",
        {"barber": barbero.pk, "date": inicio.date(), "slot_duration": 30},
    )
    assert respuesta.status_code == 200
    return respuesta.data["available_slots"]


def test_bloqueo_de_dia_completo_y_eliminacion(admin_api, agenda):
    barbero, _, inicio = agenda
    assert len(_disponibilidad(barbero, inicio)) == 6

    datos = _payload(barbero, inicio, inicio + timedelta(days=1))
    datos["start_at"] = inicio.replace(tzinfo=None).isoformat()
    datos["end_at"] = (inicio + timedelta(days=1)).replace(tzinfo=None).isoformat()
    respuesta = admin_api.post(BLOCKS, datos, format="json")
    assert respuesta.status_code == 201
    assert respuesta.data["start_at"] == inicio.isoformat()
    assert admin_api.get(BLOCKS).data == [respuesta.data]
    assert _disponibilidad(barbero, inicio) == []

    assert admin_api.delete(f"{BLOCKS}/{respuesta.data['id']}").status_code == 204
    assert admin_api.get(BLOCKS).data == []
    assert len(_disponibilidad(barbero, inicio)) == 6


def test_bloqueos_parciales_solapados_y_reserva_directa(admin_api, agenda):
    barbero, servicio, inicio = agenda
    diez = inicio + timedelta(hours=10)
    for desde, hasta in ((0, 45), (30, 60)):
        respuesta = admin_api.post(
            BLOCKS,
            _payload(
                barbero,
                diez + timedelta(minutes=desde),
                diez + timedelta(minutes=hasta),
            ),
            format="json",
        )
        assert respuesta.status_code == 201

    assert len(_disponibilidad(barbero, inicio)) == 4

    datos = {
        "barber": barbero.pk,
        "service": servicio.pk,
        "contact_name": "Ana Perez",
        "contact_phone": "3001234567",
    }
    api = APIClient(REMOTE_ADDR="192.0.2.58")
    respuesta = api.post(
        "/api/v1/appointments",
        {**datos, "start_at": (diez - timedelta(minutes=15)).isoformat()},
        format="json",
    )
    assert respuesta.status_code == 409
    respuesta = api.post(
        "/api/v1/appointments",
        {**datos, "start_at": (diez - timedelta(minutes=30)).isoformat()},
        format="json",
    )
    assert respuesta.status_code == 201
    respuesta = api.post(
        "/api/v1/appointments",
        {**datos, "start_at": (diez + timedelta(hours=1)).isoformat()},
        format="json",
    )
    assert respuesta.status_code == 201


@pytest.mark.parametrize(
    "rol, codigo", [("cliente", 403), ("barbero", 403), (None, 401)]
)
def test_endpoints_exigen_administrador(make_user, rol, codigo):
    api = APIClient()
    if rol:
        api.force_authenticate(user=make_user(rol))
    assert api.get(BLOCKS).status_code == codigo
    assert api.post(BLOCKS, {}, format="json").status_code == codigo
    assert api.delete(f"{BLOCKS}/1").status_code == codigo


def test_admin_sin_membresia_recibe_403(admin_api):
    assert admin_api.get(BLOCKS).status_code == 403


def test_bloqueos_aislados_por_barberia(admin_api, agenda, make_user):
    _, _, inicio = agenda
    barberia = Barberia.objects.create(name="Otra barbería")
    ajeno = Barbero.objects.create(barberia=barberia, name="Luis")
    datos = _payload(ajeno, inicio, inicio + timedelta(hours=1))
    assert admin_api.post(BLOCKS, datos, format="json").status_code == 400

    otro_admin = make_user("admin", email="otro-admin@barberflow.test")
    Membresia.objects.create(user=otro_admin, barberia=barberia)
    api = APIClient()
    api.force_authenticate(user=otro_admin)
    respuesta = api.post(BLOCKS, datos, format="json")
    assert respuesta.status_code == 201

    assert admin_api.get(BLOCKS).data == []
    assert admin_api.delete(f"{BLOCKS}/{respuesta.data['id']}").status_code == 404
    assert api.get(BLOCKS).data == [respuesta.data]


def test_rechaza_intervalo_invalido_y_motivo_vacio(admin_api, agenda):
    barbero, _, inicio = agenda
    datos = _payload(barbero, inicio, inicio)
    assert "end_at" in admin_api.post(BLOCKS, datos, format="json").data
    datos["end_at"] = (inicio + timedelta(hours=1)).isoformat()
    datos["reason"] = "   "
    assert "reason" in admin_api.post(BLOCKS, datos, format="json").data
