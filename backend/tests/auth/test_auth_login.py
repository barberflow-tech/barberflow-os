"""SCRUM-32 / HU-06: login, tokens JWT y endpoints protegidos (AUTH-01 a AUTH-11, AUTH-15)."""

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from conftest import AUTH_CONTRACT

pytestmark = pytest.mark.django_db

ME_URL = AUTH_CONTRACT["me_url"]


def _role_from_login(response):
    """El rol puede venir en el cuerpo de la respuesta o como claim del token."""
    body = response.json()
    if "role" in body:
        return body["role"]
    return AccessToken(body["access"]).get("role")


def test_auth01_login_valido_de_cliente_retorna_tokens_jwt(cliente, login):
    # Dado un cliente registrado
    # Cuando inicia sesion con credenciales validas
    response = login(cliente.email)

    # Entonces recibe un access y un refresh JWT validos y su rol
    assert response.status_code == 200
    body = response.json()
    assert str(AccessToken(body["access"])["user_id"]) == str(cliente.pk)
    assert body["refresh"]
    assert _role_from_login(response) == AUTH_CONTRACT["roles"]["cliente"]


@pytest.mark.parametrize("role", ["barbero", "admin"])
def test_auth02_login_valido_retorna_el_rol_para_redirigir(make_user, login, role):
    # Dado un usuario del personal con su rol
    user = make_user(role)

    # Cuando inicia sesion
    response = login(user.email)

    # Entonces el sistema le indica su rol para redirigirlo
    assert response.status_code == 200
    assert _role_from_login(response) == AUTH_CONTRACT["roles"][role]


def test_auth03_contrasena_incorrecta_retorna_401_sin_token(cliente, login):
    response = login(cliente.email, password="incorrecta-123")

    assert response.status_code == 401
    assert "access" not in response.json()


def test_auth04_usuario_inexistente_no_revela_si_el_email_existe(cliente, login):
    # Dado un email registrado y otro que no existe
    wrong_password = login(cliente.email, password="incorrecta-123")
    unknown_user = login("nadie@barberflow.test")

    # Entonces ambos fallan igual, sin revelar cual email existe
    assert unknown_user.status_code == 401
    assert unknown_user.json() == wrong_password.json()


@pytest.mark.parametrize(
    "payload",
    [{}, {"password": "algo"}, {AUTH_CONTRACT["login_field"]: "a@b.co"}],
    ids=["vacio", "sin-email", "sin-password"],
)
def test_auth05_campos_faltantes_retornan_400(api_client, payload):
    response = api_client.post(AUTH_CONTRACT["login_url"], payload, format="json")

    assert response.status_code == 400


@pytest.mark.parametrize(
    "malicious_email",
    [
        "' OR '1'='1' --",
        "' OR 1=1 --",
        "admin@barberflow.test' --",
        '" OR ""="',
        "'; DROP TABLE auth_user; --",
    ],
)
def test_auth06_inyeccion_sql_en_email_es_rechazada(admin_user, login, malicious_email):
    # Dado un intento de inyeccion SQL en el campo de email
    response = login(malicious_email)

    # Entonces el login es rechazado con 400 o 401, nunca 200 ni 500
    assert response.status_code in (400, 401)


@pytest.mark.parametrize("malicious_password", ["' OR 1=1 --", "' OR '1'='1"])
def test_auth07_inyeccion_sql_en_password_es_rechazada(
    cliente, login, malicious_password
):
    response = login(cliente.email, password=malicious_password)

    assert response.status_code == 401


def test_auth08_fuerza_bruta_nunca_concede_acceso(cliente, login):
    # Dado un atacante que prueba 10 contrasenas seguidas
    statuses = [
        login(cliente.email, password=f"intento-{i}").status_code for i in range(10)
    ]

    # Entonces ningun intento obtiene token (401, o 429 si hay limite de intentos)
    assert all(status in (401, 429) for status in statuses)


@pytest.mark.skip(
    reason="Pendiente: SCRUM-29 aun no define limite de intentos (throttling). "
    "Activar cuando Cristhian confirme el numero de intentos permitidos."
)
def test_auth08b_fuerza_bruta_bloquea_tras_varios_intentos(cliente, login):
    statuses = [
        login(cliente.email, password=f"intento-{i}").status_code for i in range(10)
    ]

    assert 429 in statuses


def test_auth09_token_expirado_retorna_401(cliente, api_client):
    # Dado un access token vencido
    token = AccessToken.for_user(cliente)
    token.set_exp(lifetime=-token.lifetime)

    # Cuando se usa en un endpoint protegido
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(ME_URL)

    # Entonces se rechaza
    assert response.status_code == 401


def test_auth10_token_manipulado_retorna_401(cliente, api_client):
    # Dado un token valido al que se le altera la firma
    token = str(AccessToken.for_user(cliente))
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")
    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_auth11_refresh_valido_entrega_nuevo_access(cliente, login, api_client):
    refresh = login(cliente.email).json()["refresh"]

    response = api_client.post(
        AUTH_CONTRACT["refresh_url"], {"refresh": refresh}, format="json"
    )

    assert response.status_code == 200
    assert str(AccessToken(response.json()["access"])["user_id"]) == str(cliente.pk)


def test_auth15_endpoint_protegido_sin_token_retorna_401(api_client):
    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_endpoint_protegido_con_token_valido_retorna_200(cliente, login, api_client):
    access = login(cliente.email).json()["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get(ME_URL)

    assert response.status_code == 200
