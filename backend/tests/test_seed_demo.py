import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio

pytestmark = pytest.mark.django_db


def test_seed_demo_crea_los_datos_y_es_idempotente(settings):
    settings.DEBUG = True

    call_command("seed_demo")
    call_command("seed_demo")

    assert Servicio.objects.count() == 4
    assert Barbero.objects.count() == 3
    assert HorarioBarbero.objects.count() == 18
    assert Membresia.objects.count() == 2
    admin = get_user_model().objects.get(username="admin@barberflow.test")
    assert admin.is_staff and admin.check_password("Demo12345!")


def test_seed_demo_se_ve_en_el_endpoint_publico(settings, client):
    settings.DEBUG = True
    call_command("seed_demo")

    respuesta = client.get("/api/v1/services")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 4


def test_seed_demo_se_niega_fuera_de_debug(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_demo")


def test_seed_demo_publica_la_descripcion_de_cada_servicio(settings, client):
    settings.DEBUG = True
    call_command("seed_demo")

    servicios = client.get("/api/v1/services").json()

    assert all(s["description"] for s in servicios)
