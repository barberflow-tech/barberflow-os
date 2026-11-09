"""SCRUM-71 / HU-09: matriz de permisos por rol.

Recorre cada endpoint protegido con cada rol (cliente, barbero, admin) y sin
sesion, con un JWT real en la cabecera (sin force_authenticate), y comprueba
el codigo esperado. Cada fila de MATRIZ es una regla de la matriz de permisos:
si un endpoint cambia de permisos (SCRUM-67/68), se cambia aqui su fila.

El personal (barbero y admin) pertenece a la barberia del catalogo, como en
seed_demo; el cliente no tiene membresia, como un cliente recien registrado.
"""

from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio

pytestmark = pytest.mark.django_db

ROLES = ["anonimo", "cliente", "barbero", "admin"]


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def escenario(make_user):
    """Barberia del catalogo con un barbero vinculado, un servicio y usuarios."""
    barberia = obtener_barberia_catalogo()
    usuarios = {
        "cliente": make_user("cliente"),
        "barbero": make_user("barbero"),
        "admin": make_user("admin"),
    }
    for rol in ("barbero", "admin"):
        Membresia.objects.create(user=usuarios[rol], barberia=barberia)

    barbero = Barbero.objects.create(
        barberia=barberia, name="Thiago", user=usuarios["barbero"]
    )
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero, weekday=dia, open_time=time(8), close_time=time(20)
        )
    servicio = Servicio.objects.create(
        barberia=barberia,
        name="Corte",
        price=Decimal("30000.00"),
        duration_minutes=30,
    )
    return {"usuarios": usuarios, "barbero": barbero, "servicio": servicio}


def _cliente_http(escenario, rol):
    api = APIClient()
    if rol != "anonimo":
        token = AccessToken.for_user(escenario["usuarios"][rol])
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


def _manana(hora):
    return (timezone.now() + timedelta(days=1)).replace(
        hour=hora, minute=0, second=0, microsecond=0
    )


# --- Peticiones de la matriz ---------------------------------------------
# Cada una recibe (api, escenario, rol) y devuelve la respuesta.


def listar_servicios(api, e, rol):
    return api.get("/api/v1/services")


def ver_servicio(api, e, rol):
    return api.get(f"/api/v1/services/{e['servicio'].pk}")


def crear_servicio(api, e, rol):
    return api.post(
        "/api/v1/services",
        {"name": f"Barba {rol}", "price": "20000.00", "duration_minutes": 30},
        format="json",
    )


def editar_servicio(api, e, rol):
    return api.put(
        f"/api/v1/services/{e['servicio'].pk}",
        {"name": "Corte editado", "price": "32000.00", "duration_minutes": 30},
        format="json",
    )


def borrar_servicio(api, e, rol):
    return api.delete(f"/api/v1/services/{e['servicio'].pk}")


def ver_disponibilidad(api, e, rol):
    return api.get(
        "/api/v1/availability",
        {
            "barber": e["barbero"].pk,
            "date": _manana(10).date().isoformat(),
            "slot_duration": 30,
        },
    )


def crear_cita(api, e, rol):
    # Cada rol pide una hora distinta para que no choquen entre filas.
    hora = {"anonimo": 9, "cliente": 10, "barbero": 11, "admin": 12}[rol]
    payload = {
        "barber": e["barbero"].pk,
        "service": e["servicio"].pk,
        "start_at": _manana(hora).isoformat(),
    }
    if rol == "anonimo":
        payload.update(contact_name="Ana Perez", contact_phone="3001234567")
    return api.post("/api/v1/appointments", payload, format="json")


def ver_portafolio(api, e, rol):
    return api.get("/api/v1/barbers/me/portfolio")


def subir_portafolio(api, e, rol):
    # Sin archivo: si el permiso pasa, responde 400 por el campo faltante,
    # nunca llega a Storage.
    return api.post("/api/v1/barbers/me/portfolio", {}, format="multipart")


def endpoint_solo_admin(api, e, rol):
    return api.get("/api/v1/auth/protected-test")


# --- Matriz: endpoint -> codigo esperado por rol --------------------------
#             (anonimo, cliente, barbero, admin)

MATRIZ = {
    "GET /services": (listar_servicios, (200, 200, 200, 200)),
    "GET /services/{id}": (ver_servicio, (200, 200, 200, 200)),
    "POST /services": (crear_servicio, (401, 403, 403, 201)),
    "PUT /services/{id}": (editar_servicio, (401, 403, 403, 200)),
    "DELETE /services/{id}": (borrar_servicio, (401, 403, 403, 204)),
    "GET /availability": (ver_disponibilidad, (200, 200, 200, 200)),
    "POST /appointments": (crear_cita, (201, 201, 201, 201)),
    "GET /barbers/me/portfolio": (ver_portafolio, (401, 403, 200, 403)),
    "POST /barbers/me/portfolio": (subir_portafolio, (401, 403, 400, 403)),
    "GET /auth/protected-test": (endpoint_solo_admin, (401, 403, 403, 200)),
}

CASOS = [
    pytest.param(peticion, rol, esperados[i], id=f"{endpoint} [{rol}]")
    for endpoint, (peticion, esperados) in MATRIZ.items()
    for i, rol in enumerate(ROLES)
]


@pytest.mark.parametrize("peticion,rol,esperado", CASOS)
def test_matriz_de_permisos(escenario, peticion, rol, esperado):
    # Dado un usuario con ese rol (o sin sesion)
    api = _cliente_http(escenario, rol)

    # Cuando llama al endpoint
    response = peticion(api, escenario, rol)

    # Entonces recibe exactamente el codigo de la matriz
    assert response.status_code == esperado, response.content[:300]


# --- Casos que la matriz no cubre por si sola -----------------------------

PROTEGIDOS = [
    pytest.param(peticion, id=endpoint)
    for endpoint, (peticion, esperados) in MATRIZ.items()
    if esperados[0] == 401
]


@pytest.mark.parametrize("peticion", PROTEGIDOS)
def test_token_alterado_da_401_en_todo_endpoint_protegido(escenario, peticion):
    # Un token de admin con la firma alterada no vale ni como admin ni como anonimo
    token = str(AccessToken.for_user(escenario["usuarios"]["admin"]))
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token[:-4]}AAAA")

    assert peticion(api, escenario, "admin").status_code == 401


@pytest.mark.parametrize("peticion", PROTEGIDOS)
def test_token_vencido_da_401_en_todo_endpoint_protegido(escenario, peticion):
    token = AccessToken.for_user(escenario["usuarios"]["admin"])
    token.set_exp(lifetime=-token.lifetime)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    assert peticion(api, escenario, "admin").status_code == 401


def test_cambio_de_rol_surte_efecto_sin_nuevo_token(escenario):
    # Dado un cliente con un token emitido cuando aun era cliente
    cliente = escenario["usuarios"]["cliente"]
    api = _cliente_http(escenario, "cliente")
    assert endpoint_solo_admin(api, escenario, "cliente").status_code == 403

    # Cuando el admin lo asciende a admin, el mismo token ya da acceso
    cliente.perfil.role = "admin"
    cliente.perfil.save()
    assert endpoint_solo_admin(api, escenario, "cliente").status_code == 200

    # Y cuando le quita el rol, pierde el acceso de inmediato
    cliente.perfil.role = "cliente"
    cliente.perfil.save()
    assert endpoint_solo_admin(api, escenario, "cliente").status_code == 403
