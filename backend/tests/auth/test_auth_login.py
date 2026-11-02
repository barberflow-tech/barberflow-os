"""SCRUM-32 / HU-06: login, refresh por cookie y endpoint protegido.

Cubre AUTH-01 a AUTH-11 y AUTH-15 contra el contrato de SCRUM-29 (ver
AUTH_CONTRACT en conftest.py).
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from conftest import AUTH_CONTRACT, refresh_cookie

pytestmark = pytest.mark.django_db

LOGIN_URL = AUTH_CONTRACT["login_url"]
REFRESH_URL = AUTH_CONTRACT["refresh_url"]
PROTECTED_URL = AUTH_CONTRACT["protected_url"]
ROLES = AUTH_CONTRACT["roles"]


def _assert_cookie_borrada(response):
    cookie = refresh_cookie(response) or next(iter(response.cookies.values()), None)
    assert cookie is not None, "el refresh fallido debe borrar la cookie"
    assert cookie.value == ""


# --- Login ---------------------------------------------------------------


def test_auth01_login_valido_de_cliente_retorna_access_y_cookie_refresh(cliente, login):
    # Dado un cliente registrado
    # Cuando inicia sesion con credenciales validas
    response = login(cliente.email)

    # Entonces recibe el access en el cuerpo con sus datos
    assert response.status_code == 200
    body = response.json()
    assert str(AccessToken(body["access"])["user_id"]) == str(cliente.pk)
    assert body["user"] == {
        "id": cliente.pk,
        "email": cliente.email,
        "role": ROLES["cliente"],
    }
    # Y el refresh viaja solo en una cookie HttpOnly, nunca en el cuerpo
    assert "refresh" not in body
    cookie = refresh_cookie(response)
    assert cookie is not None
    assert cookie.value


@pytest.mark.parametrize("role", ["barbero", "admin"])
def test_auth02_login_valido_retorna_el_rol_para_redirigir(make_user, login, role):
    # Dado un usuario del personal con su rol
    user = make_user(role)

    # Cuando inicia sesion
    response = login(user.email)

    # Entonces el sistema le indica su rol, en minusculas, para redirigirlo
    assert response.status_code == 200
    assert response.json()["user"]["role"] == ROLES[role]


def test_auth03_contrasena_incorrecta_retorna_401_sin_token(cliente, login):
    response = login(cliente.email, password="incorrecta-123")

    assert response.status_code == 401
    assert "access" not in response.json()
    assert refresh_cookie(response) is None


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
    response = api_client.post(LOGIN_URL, payload, format="json")

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


# --- Refresh por cookie --------------------------------------------------


def test_auth11_refresh_con_cookie_valida_entrega_nuevo_access(
    cliente, login, api_client
):
    # Dado un cliente que inicio sesion (api_client ya guarda la cookie)
    login(cliente.email)

    # Cuando pide un access nuevo sin mandar nada en el cuerpo
    response = api_client.post(REFRESH_URL)

    # Entonces recibe un access nuevo y sus datos
    assert response.status_code == 200
    body = response.json()
    assert str(AccessToken(body["access"])["user_id"]) == str(cliente.pk)
    assert body["user"]["role"] == ROLES["cliente"]
    assert "refresh" not in body


def test_auth11b_refresh_sin_cookie_retorna_401():
    response = APIClient().post(REFRESH_URL)

    assert response.status_code == 401


def test_auth11c_refresh_con_cookie_expirada_retorna_401_y_borra_la_cookie(
    cliente, login, api_client
):
    # Dado un cliente con sesion, pero cuyo refresh ya vencio
    cookie_name = refresh_cookie(login(cliente.email)).key
    expired = RefreshToken.for_user(cliente)
    expired.set_exp(lifetime=-expired.lifetime)
    api_client.cookies[cookie_name] = str(expired)

    # Cuando intenta renovar la sesion
    response = api_client.post(REFRESH_URL)

    # Entonces recibe 401 y el servidor borra la cookie
    assert response.status_code == 401
    _assert_cookie_borrada(response)


def test_auth11d_refresh_con_cookie_alterada_retorna_401_y_borra_la_cookie(
    cliente, login, api_client
):
    cookie_name = refresh_cookie(login(cliente.email)).key
    api_client.cookies[cookie_name] = "token-alterado"

    response = api_client.post(REFRESH_URL)

    assert response.status_code == 401
    _assert_cookie_borrada(response)


# --- Endpoint protegido con HasRole("admin") -----------------------------


def test_auth09_token_expirado_retorna_401(admin_user, api_client):
    # Dado un access token vencido
    token = AccessToken.for_user(admin_user)
    token.set_exp(lifetime=-token.lifetime)

    # Cuando se usa en un endpoint protegido
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(PROTECTED_URL)

    # Entonces se rechaza
    assert response.status_code == 401


def test_auth10_token_manipulado_retorna_401(admin_user, api_client):
    # Dado un token valido al que se le altera la firma
    token = str(AccessToken.for_user(admin_user))
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")
    response = api_client.get(PROTECTED_URL)

    assert response.status_code == 401


def test_auth15_endpoint_protegido_sin_token_retorna_401(api_client):
    response = api_client.get(PROTECTED_URL)

    assert response.status_code == 401


def test_endpoint_protegido_con_token_de_admin_retorna_200(
    admin_user, login, api_client
):
    access = login(admin_user.email).json()["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get(PROTECTED_URL)

    assert response.status_code == 200


@pytest.mark.parametrize("role", ["cliente", "barbero"])
def test_endpoint_protegido_con_rol_sin_permiso_retorna_403(
    make_user, login, api_client, role
):
    # Dado un usuario autenticado que no es admin
    access = login(make_user(role).email).json()["access"]

    # Cuando entra a un endpoint con HasRole("admin")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get(PROTECTED_URL)

    # Entonces queda autenticado pero sin permiso
    assert response.status_code == 403
