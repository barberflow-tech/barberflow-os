"""POST /api/v1/auth/logout: la sesion no debe revivir tras cerrar sesion."""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
REFRESH = "/api/v1/auth/refresh"
EMAIL = "user@test.com"
CONTRASENA = "Corte.Fade-2026"
COOKIE = "refresh_token"


@pytest.fixture
def sesion(django_user_model):
    django_user_model.objects.create_user(
        username=EMAIL, email=EMAIL, password=CONTRASENA
    )
    api = APIClient()
    respuesta = api.post(LOGIN, {"email": EMAIL, "password": CONTRASENA}, format="json")
    assert respuesta.status_code == 200
    return api


def test_logout_borra_la_cookie_y_el_refresh_deja_de_funcionar(sesion):
    # Dado un usuario con sesion iniciada
    # Cuando cierra sesion
    respuesta = sesion.post(LOGOUT)

    # Entonces la cookie se borra y ya no puede renovar el access token
    assert respuesta.status_code == 204
    cookie = respuesta.cookies[COOKIE]
    assert cookie.value == "" and int(cookie["max-age"]) == 0
    assert sesion.post(REFRESH).status_code == 401


def test_logout_sin_sesion_es_idempotente():
    assert APIClient().post(LOGOUT).status_code == 204


def test_logout_rechaza_un_origen_no_autorizado():
    respuesta = APIClient().post(LOGOUT, HTTP_ORIGIN="https://sitio-malicioso.example")

    assert respuesta.status_code == 403
