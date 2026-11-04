from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

URL = "/api/v1/services"
MOCK_BARBERIA_NAME = "BarberFlow Demo (contexto temporal)"


@pytest.fixture
def barberia():
    return Barberia.objects.get_or_create(
        name=MOCK_BARBERIA_NAME,
        defaults={"is_active": True},
    )[0]


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clásico",
        price=Decimal("20000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def administrador(django_user_model):
    return django_user_model.objects.create_user(
        username="admin_catalogo",
        password="test-password",
        is_staff=True,
    )


@pytest.fixture
def api_admin(administrador):
    api = APIClient()
    api.force_authenticate(user=administrador)
    return api


@pytest.fixture
def api_publica():
    return APIClient()


@pytest.mark.django_db
def test_admin_crea_servicio_y_retorna_201(api_admin):
    # Dado un administrador y los datos de un nuevo servicio
    payload = {
        "name": "Corte + Barba",
        "price": "35000.00",
        "duration_minutes": 45,
        "is_active": True,
    }

    # Cuando envía POST /api/v1/services
    response = api_admin.post(URL, payload, format="json")

    # Entonces el servicio queda persistido y se retorna HTTP 201
    assert response.status_code == 201
    servicio = Servicio.objects.get(pk=response.data["id"])
    assert servicio.name == "Corte + Barba"
    assert servicio.price == Decimal("35000.00")
    assert servicio.duration_minutes == 45


@pytest.mark.django_db
def test_catalogo_publico_no_muestra_servicios_inactivos(
    api_publica, barberia, servicio
):
    # Dado un servicio activo y otro deshabilitado
    inactivo = Servicio.objects.create(
        barberia=barberia,
        name="Barba clásica",
        price=Decimal("15000.00"),
        duration_minutes=20,
        is_active=False,
    )

    # Cuando un visitante consulta el catálogo público
    response = api_publica.get(URL)

    # Entonces solo recibe los servicios activos
    assert response.status_code == 200
    ids = {item["id"] for item in response.data}
    assert servicio.pk in ids
    assert inactivo.pk not in ids


@pytest.mark.django_db
def test_usuario_no_administrador_no_puede_crear_servicios(
    api_publica, django_user_model
):
    usuario = django_user_model.objects.create_user(
        username="usuario_normal",
        password="test-password",
    )
    api_publica.force_authenticate(user=usuario)

    response = api_publica.post(
        URL,
        {
            "name": "Cejas",
            "price": "8000.00",
            "duration_minutes": 15,
        },
        format="json",
    )

    assert response.status_code == 403
    assert not Servicio.objects.filter(name="Cejas").exists()


@pytest.mark.django_db
def test_visitante_no_autenticado_no_puede_crear_servicios(api_publica):
    response = api_publica.post(
        URL,
        {
            "name": "Cejas",
            "price": "8000.00",
            "duration_minutes": 15,
        },
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_put_actualiza_precio_sin_alterar_precio_historico(
    api_admin, barberia, servicio, administrador
):
    # Dado un servicio de $20.000 y una cita histórica con ese precio
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    inicio = timezone.now() + timedelta(days=1)
    cita = Cita.objects.create(
        barberia=barberia,
        client=administrador,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        status=Cita.Estado.COMPLETED,
        price=Decimal("20000.00"),
    )

    # Cuando el administrador cambia el precio a $25.000
    response = api_admin.put(
        f"{URL}/{servicio.pk}",
        {
            "name": servicio.name,
            "price": "25000.00",
            "duration_minutes": 30,
            "is_active": True,
        },
        format="json",
    )

    # Entonces cambia el catálogo, pero la cita conserva su precio histórico
    assert response.status_code == 200
    servicio.refresh_from_db()
    cita.refresh_from_db()
    assert servicio.price == Decimal("25000.00")
    assert cita.price == Decimal("20000.00")


@pytest.mark.django_db
def test_delete_desactiva_servicio_y_conserva_cita_historica(
    api_admin, barberia, servicio, administrador
):
    # Dado un servicio asociado a una cita histórica
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    inicio = timezone.now() + timedelta(days=2)
    cita = Cita.objects.create(
        barberia=barberia,
        client=administrador,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        status=Cita.Estado.COMPLETED,
        price=servicio.price,
    )

    # Cuando el administrador elimina el servicio del catálogo
    response = api_admin.delete(f"{URL}/{servicio.pk}")

    # Entonces se desactiva lógicamente y la cita permanece intacta
    assert response.status_code == 204
    servicio.refresh_from_db()
    cita.refresh_from_db()
    assert servicio.is_active is False
    assert cita.service_id == servicio.pk
    assert cita.price == Decimal("20000.00")


@pytest.mark.django_db
def test_put_rechaza_precio_negativo(api_admin, servicio):
    response = api_admin.put(
        f"{URL}/{servicio.pk}",
        {
            "name": servicio.name,
            "price": "-1.00",
            "duration_minutes": 30,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 400
    servicio.refresh_from_db()
    assert servicio.price == Decimal("20000.00")


@pytest.mark.django_db
def test_post_rechaza_duracion_cero(api_admin):
    response = api_admin.post(
        URL,
        {
            "name": "Servicio inválido",
            "price": "10000.00",
            "duration_minutes": 0,
        },
        format="json",
    )

    assert response.status_code == 400
    assert not Servicio.objects.filter(name="Servicio inválido").exists()
