"""SCRUM-29 / HU-06: GET /api/v1/auth/protected-test (JWT + autenticacion + HasRole)."""

from datetime import timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.usuarios.models import Rol

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
URL = "/api/v1/auth/protected-test"
CONTRASENA = "Corte.Fade-2026"


@pytest.fixture
def api():
    return APIClient()


def _crear(django_user_model, rol):
    email = f"{rol}@test.com"
    usuario = django_user_model.objects.create_user(
        username=email, email=email, password=CONTRASENA
    )
    usuario.perfil.role = rol
    usuario.perfil.save()
    return usuario


def _iniciar_sesion(api, usuario):
    """Login real: devuelve el access token que recibiria el frontend."""
    respuesta = api.post(
        LOGIN, {"email": usuario.email, "password": CONTRASENA}, format="json"
    )
    assert respuesta.status_code == 200
    return respuesta.json()["access"]


def _get(api, token=None, **extra):
    if token is not None:
        extra["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return api.get(URL, **extra)


# --- Casos obligatorios --------------------------------------------------


def test_cliente_recibe_403(api, django_user_model):
    # Dado un cliente con sesion iniciada
    cliente = _crear(django_user_model, "cliente")
    token = _iniciar_sesion(api, cliente)

    # Cuando llama al endpoint protegido con HasRole("admin")
    respuesta = _get(api, token)

    # Entonces recibe 403 Forbidden
    assert respuesta.status_code == 403
    assert respuesta.json() == {
        "detail": "No tienes permiso para realizar esta accion."
    }


def test_admin_recibe_200(api, django_user_model):
    # Dado un admin con sesion iniciada
    admin = _crear(django_user_model, "admin")
    token = _iniciar_sesion(api, admin)

    # Cuando llama al endpoint protegido
    respuesta = _get(api, token)

    # Entonces recibe 200 con sus datos
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "detail": "Acceso concedido.",
        "user": {"id": admin.pk, "email": "admin@test.com", "role": "admin"},
    }


# --- Autenticacion JWT ---------------------------------------------------


def test_barbero_recibe_403(api, django_user_model):
    barbero = _crear(django_user_model, "barbero")

    assert _get(api, _iniciar_sesion(api, barbero)).status_code == 403


def test_sin_token_recibe_401(api):
    assert _get(api).status_code == 401


def test_token_expirado_recibe_401(api, django_user_model):
    # Dado un access token vencido de un admin
    admin = _crear(django_user_model, "admin")
    token = AccessToken(_iniciar_sesion(api, admin))
    token.set_exp(lifetime=-timedelta(seconds=1))

    assert _get(api, str(token)).status_code == 401


def test_token_con_la_firma_alterada_recibe_401(api, django_user_model):
    admin = _crear(django_user_model, "admin")
    token = _iniciar_sesion(api, admin)
    alterado = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    assert _get(api, alterado).status_code == 401


def test_token_mal_formado_recibe_401(api):
    assert _get(api, "esto-no-es-un-jwt").status_code == 401


def test_un_refresh_token_no_sirve_como_access(api, django_user_model):
    admin = _crear(django_user_model, "admin")

    assert _get(api, str(RefreshToken.for_user(admin))).status_code == 401


def test_usuario_inactivo_con_token_vigente_recibe_401(api, django_user_model):
    admin = _crear(django_user_model, "admin")
    token = _iniciar_sesion(api, admin)
    admin.is_active = False
    admin.save()

    assert _get(api, token).status_code == 401


def test_la_cabecera_debe_usar_el_esquema_bearer(api, django_user_model):
    admin = _crear(django_user_model, "admin")
    token = _iniciar_sesion(api, admin)

    respuesta = api.get(URL, HTTP_AUTHORIZATION=f"Token {token}")

    assert respuesta.status_code == 401


# --- Permisos por rol ----------------------------------------------------


def test_el_access_renovado_con_refresh_tambien_abre_el_recurso(api, django_user_model):
    # Dado un admin que renueva su sesion con la cookie del refresh
    admin = _crear(django_user_model, "admin")
    _iniciar_sesion(api, admin)
    nuevo = api.post(REFRESH).json()["access"]

    # Entonces el access nuevo pasa la autenticacion y el permiso
    assert _get(APIClient(), nuevo).status_code == 200


def test_un_admin_degradado_pierde_el_acceso_con_su_token_vigente(
    api, django_user_model
):
    # Dado un admin con un access token todavia vigente
    admin = _crear(django_user_model, "admin")
    token = _iniciar_sesion(api, admin)
    assert _get(api, token).status_code == 200

    # Cuando es degradado a cliente
    admin.perfil.role = Rol.CLIENTE
    admin.perfil.save()

    # Entonces el mismo token ya no abre el recurso
    assert _get(api, token).status_code == 403


def test_un_cliente_ascendido_gana_el_acceso_con_su_token_vigente(
    api, django_user_model
):
    cliente = _crear(django_user_model, "cliente")
    token = _iniciar_sesion(api, cliente)
    assert _get(api, token).status_code == 403

    cliente.perfil.role = Rol.ADMIN
    cliente.perfil.save()

    assert _get(api, token).status_code == 200


def test_un_superusuario_con_rol_cliente_recibe_403(api, django_user_model):
    root = django_user_model.objects.create_superuser(
        username="root@test.com", email="root@test.com", password=CONTRASENA
    )
    root.perfil.role = Rol.CLIENTE
    root.perfil.save()

    assert _get(api, _iniciar_sesion(api, root)).status_code == 403


# --- Ruta y metodos ------------------------------------------------------


def test_acepta_la_ruta_con_barra_final(api, django_user_model):
    token = _iniciar_sesion(api, _crear(django_user_model, "admin"))

    respuesta = api.get(URL + "/", HTTP_AUTHORIZATION=f"Bearer {token}")

    assert respuesta.status_code == 200


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_solo_acepta_get(api, django_user_model, metodo):
    token = _iniciar_sesion(api, _crear(django_user_model, "admin"))

    respuesta = getattr(api, metodo)(URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert respuesta.status_code == 405
