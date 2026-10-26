"""Fixtures compartidas para las pruebas del backend.

Las rutas y nombres de campos de autenticacion viven en AUTH_CONTRACT para
ajustarlos en un solo lugar cuando SCRUM-29 (endpoints de Auth) defina los
definitivos.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

AUTH_CONTRACT = {
    "register_url": "/api/auth/register/",
    "login_url": "/api/auth/login/",
    "refresh_url": "/api/auth/refresh/",
    "me_url": "/api/auth/me/",
    "login_field": "email",
    "roles": {"cliente": "CLIENTE", "barbero": "BARBERO", "admin": "ADMIN"},
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
    """Hace POST al login y devuelve la respuesta."""

    def _login(email, password=DEFAULT_PASSWORD):
        payload = {AUTH_CONTRACT["login_field"]: email, "password": password}
        return api_client.post(AUTH_CONTRACT["login_url"], payload, format="json")

    return _login
