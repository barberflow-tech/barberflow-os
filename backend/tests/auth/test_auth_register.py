"""SCRUM-32 / HU-06: registro de clientes (AUTH-12 a AUTH-14)."""

import pytest
from django.contrib.auth import get_user_model

from conftest import AUTH_CONTRACT

pytestmark = pytest.mark.django_db

REGISTER_URL = AUTH_CONTRACT["register_url"]
STRONG_PASSWORD = "Corte.Fade-2026"


def _register(api_client, **overrides):
    payload = {"email": "nuevo@barberflow.test", "password": STRONG_PASSWORD}
    payload.update(overrides)
    return api_client.post(REGISTER_URL, payload, format="json")


def test_auth12_registro_valido_guarda_la_contrasena_con_hash(api_client):
    # Dado un visitante con datos completos
    # Cuando se registra
    response = _register(api_client)

    # Entonces la cuenta se crea y la contrasena no queda en texto plano
    assert response.status_code == 201
    user = get_user_model().objects.get(email="nuevo@barberflow.test")
    assert user.password != STRONG_PASSWORD
    assert user.check_password(STRONG_PASSWORD)
    assert "password" not in response.json()


def test_auth12b_registro_publico_crea_rol_cliente(api_client):
    # Dado un visitante que intenta registrarse como administrador
    response = _register(api_client, role=AUTH_CONTRACT["roles"]["admin"])

    # Entonces la cuenta se crea, pero nunca con privilegios de personal
    assert response.status_code == 201
    user = get_user_model().objects.get(email="nuevo@barberflow.test")
    assert not user.is_staff
    assert not user.is_superuser
    if hasattr(user, "role"):
        assert user.role == AUTH_CONTRACT["roles"]["cliente"]


def test_auth13_registro_con_email_duplicado_retorna_400(api_client, cliente):
    response = _register(api_client, email=cliente.email)

    assert response.status_code == 400


@pytest.mark.parametrize("weak_password", ["123", "password", "12345678"])
def test_auth14_contrasena_debil_retorna_400(api_client, weak_password):
    response = _register(api_client, password=weak_password)

    assert response.status_code == 400
    assert not get_user_model().objects.filter(email="nuevo@barberflow.test").exists()
