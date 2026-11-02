"""Fixtures compartidas para las pruebas del backend.

Las rutas y nombres de autenticacion viven en AUTH_CONTRACT para ajustarlos en
un solo lugar. El contrato sale de SCRUM-29 y es el mismo que ya usa el
frontend (lib/authApi.ts y stores/useAuthStore.ts):

* POST /api/v1/auth/login -> 200 con {"access", "user": {id, email, role}} en el
  cuerpo y el refresh token en una cookie HttpOnly.
* POST /api/v1/auth/refresh -> lee la cookie y devuelve {"access", "user"}; si la
  cookie falta o expiro, 401 y borra la cookie.
* HasRole("admin") con los roles en minusculas.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

AUTH_CONTRACT = {
    "login_url": "/api/v1/auth/login",
    "refresh_url": "/api/v1/auth/refresh",
    # Endpoint de prueba protegido con HasRole("admin").
    # TODO(SCRUM-29): confirmar la ruta definitiva con Cristhian.
    "protected_url": "/api/v1/auth/protected-test",
    "login_field": "email",
    "roles": {"cliente": "cliente", "barbero": "barbero", "admin": "admin"},
}

DEFAULT_PASSWORD = "Barber.Flow-2026"


def _model_has_field(model, name):
    return any(field.name == name for field in model._meta.get_fields())


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    """Crea un usuario con el rol indicado ("cliente", "barbero" o "admin")."""
    user_model = get_user_model()

    def _make_user(role="cliente", email=None, password=DEFAULT_PASSWORD):
        email = email or f"{role}@barberflow.test"
        fields = {"email": email}
        if user_model.USERNAME_FIELD != "email":
            fields[user_model.USERNAME_FIELD] = email
        if _model_has_field(user_model, "role"):
            fields["role"] = AUTH_CONTRACT["roles"][role]
        if role == "admin":
            fields["is_staff"] = True
        return user_model.objects.create_user(password=password, **fields)

    return _make_user


@pytest.fixture
def cliente(make_user):
    return make_user("cliente")


@pytest.fixture
def barbero(make_user):
    return make_user("barbero")


@pytest.fixture
def admin_user(make_user):
    return make_user("admin")


@pytest.fixture
def login(api_client):
    """Hace POST al login y devuelve la respuesta.

    APIClient guarda las cookies de la respuesta, asi que despues de un login
    exitoso el mismo api_client ya lleva la cookie del refresh.
    """

    def _login(email, password=DEFAULT_PASSWORD):
        payload = {AUTH_CONTRACT["login_field"]: email, "password": password}
        return api_client.post(AUTH_CONTRACT["login_url"], payload, format="json")

    return _login


def refresh_cookie(response):
    """Devuelve la cookie HttpOnly que trae el refresh token, o None."""
    for morsel in response.cookies.values():
        if morsel["httponly"]:
            return morsel
    return None
