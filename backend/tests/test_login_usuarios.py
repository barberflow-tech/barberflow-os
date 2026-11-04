"""SCRUM-29 / HU-06: POST /api/v1/auth/login con refresh token en cookie."""

import pytest
from django.http import HttpResponse
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.usuarios.cookies import borrar_cookie_refresh, poner_cookie_refresh
from apps.usuarios.models import Rol

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/login"
EMAIL = "user@test.com"
CONTRASENA = "Corte.Fade-2026"
COOKIE = "refresh_token"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user(
        username=EMAIL, email=EMAIL, password=CONTRASENA
    )


def _login(api, email=EMAIL, password=CONTRASENA, **extra):
    return api.post(URL, {"email": email, "password": password}, format="json", **extra)


# --- Login correcto ------------------------------------------------------


def test_login_correcto_retorna_200_con_access_y_usuario(api, usuario):
    # Dado un cliente registrado
    # Cuando inicia sesion con credenciales validas
    respuesta = _login(api)

    # Entonces recibe exactamente access y user {id, email, role}
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "access": respuesta.json()["access"],
        "user": {"id": usuario.pk, "email": EMAIL, "role": "cliente"},
    }
    access = AccessToken(respuesta.json()["access"])
    assert access["user_id"] == usuario.pk
    assert access["email"] == EMAIL
    assert access["role"] == "cliente"


@pytest.mark.parametrize("rol", [Rol.BARBERO, Rol.ADMIN])
def test_login_devuelve_el_rol_del_personal_para_redirigir(api, usuario, rol):
    usuario.perfil.role = rol
    usuario.perfil.save()

    respuesta = _login(api)

    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["role"] == rol.value
    assert AccessToken(respuesta.json()["access"])["role"] == rol.value


def test_login_no_distingue_mayusculas_ni_espacios_en_el_email(api, usuario):
    respuesta = _login(api, email="  USER@Test.COM ")

    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["email"] == EMAIL


def test_login_funciona_con_un_superusuario_cuyo_username_no_es_el_email(
    api, django_user_model
):
    # Dado un usuario creado con createsuperuser (username distinto del email)
    django_user_model.objects.create_superuser(
        username="root", email="root@test.com", password=CONTRASENA
    )

    respuesta = _login(api, email="root@test.com")

    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["email"] == "root@test.com"


def test_un_usuario_registrado_por_el_endpoint_puede_iniciar_sesion(api):
    registro = api.post(
        "/api/v1/auth/register",
        {"email": "nuevo@test.com", "password": CONTRASENA},
        format="json",
    )
    assert registro.status_code == 201

    respuesta = _login(api, email="nuevo@test.com")

    assert respuesta.status_code == 200
    assert respuesta.json()["user"]["role"] == "cliente"


def test_el_access_del_login_autentica_peticiones(api, usuario):
    access = _login(api).json()["access"]
    request = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {access}")

    user, _ = JWTAuthentication().authenticate(request)

    assert user.pk == usuario.pk


def test_login_acepta_la_ruta_con_barra_final(api, usuario):
    respuesta = api.post(
        URL + "/", {"email": EMAIL, "password": CONTRASENA}, format="json"
    )

    assert respuesta.status_code == 200


def test_login_ignora_un_token_invalido_en_la_cabecera(api, usuario):
    # Dado un navegador con un access token vencido
    api.credentials(HTTP_AUTHORIZATION="Bearer token-vencido")

    # Entonces iniciar sesion igual funciona
    assert _login(api).status_code == 200


def test_login_solo_acepta_post(api):
    assert api.get(URL).status_code == 405


def test_la_respuesta_con_tokens_no_se_guarda_en_cache(api, usuario):
    assert _login(api).headers["Cache-Control"] == "no-store"


# --- El refresh token solo viaja en la cookie ---------------------------


def test_el_refresh_token_no_aparece_en_el_cuerpo(api, usuario):
    respuesta = _login(api)

    refresh = respuesta.cookies[COOKIE].value
    assert "refresh" not in respuesta.json()
    assert "refresh" not in respuesta.json()["user"]
    assert refresh not in respuesta.content.decode()


def test_la_cookie_del_refresh_se_crea_con_los_atributos_de_seguridad(api, usuario):
    # Cuando el login es correcto
    respuesta = _login(api)

    # Entonces llega una cookie HttpOnly, con SameSite, acotada a /auth/
    cookie = respuesta.cookies[COOKIE]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/v1/auth/"
    assert int(cookie["max-age"]) == int(
        api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()
    )
    assert not cookie["domain"]


def test_la_cookie_contiene_un_refresh_token_valido_con_claims(api, usuario):
    respuesta = _login(api)

    refresh = RefreshToken(respuesta.cookies[COOKIE].value)
    assert refresh["token_type"] == "refresh"
    assert refresh["user_id"] == usuario.pk
    assert refresh["email"] == EMAIL
    assert refresh["role"] == "cliente"


def test_el_cliente_de_pruebas_guarda_la_cookie_para_el_refresh(api, usuario):
    # Dado un login correcto, el navegador (APIClient) conserva la cookie
    _login(api)

    assert api.cookies[COOKIE].value


@pytest.mark.parametrize("secure", [True, False])
def test_secure_de_la_cookie_se_configura_por_entorno(api, usuario, settings, secure):
    settings.AUTH_REFRESH_COOKIE = {**settings.AUTH_REFRESH_COOKIE, "SECURE": secure}

    cookie = _login(api).cookies[COOKIE]

    assert bool(cookie["secure"]) is secure


@pytest.mark.parametrize("samesite", ["Lax", "Strict", "None"])
def test_samesite_de_la_cookie_se_configura_por_entorno(
    api, usuario, settings, samesite
):
    settings.AUTH_REFRESH_COOKIE = {
        **settings.AUTH_REFRESH_COOKIE,
        "SAMESITE": samesite,
        "SECURE": True,
    }

    assert _login(api).cookies[COOKIE]["samesite"] == samesite


def test_el_nombre_de_la_cookie_se_configura_por_entorno(api, usuario, settings):
    settings.AUTH_REFRESH_COOKIE = {**settings.AUTH_REFRESH_COOKIE, "NAME": "rt"}

    respuesta = _login(api)

    assert "rt" in respuesta.cookies
    assert COOKIE not in respuesta.cookies


def test_borrar_la_cookie_usa_el_mismo_path_para_que_el_navegador_la_elimine():
    respuesta = HttpResponse()
    poner_cookie_refresh(respuesta, "token")

    borrar_cookie_refresh(respuesta)

    cookie = respuesta.cookies[COOKIE]
    assert cookie.value == ""
    assert cookie["path"] == "/api/v1/auth/"
    assert int(cookie["max-age"]) == 0
    assert cookie["samesite"] == "Lax"


# --- Credenciales invalidas ---------------------------------------------


def test_contrasena_incorrecta_retorna_401_sin_token_ni_cookie(api, usuario):
    respuesta = _login(api, password="incorrecta-123")

    assert respuesta.status_code == 401
    assert "access" not in respuesta.json()
    assert COOKIE not in respuesta.cookies


def test_email_inexistente_responde_igual_que_contrasena_incorrecta(api, usuario):
    # Dado un email registrado y otro que no existe
    incorrecta = _login(api, password="incorrecta-123")
    inexistente = _login(api, email="nadie@test.com")

    # Entonces ambos fallan igual, sin revelar cual email existe
    assert inexistente.status_code == 401
    assert inexistente.json() == incorrecta.json()
    assert COOKIE not in inexistente.cookies


def test_usuario_inactivo_no_puede_iniciar_sesion(api, usuario):
    usuario.is_active = False
    usuario.save()

    respuesta = _login(api)

    assert respuesta.status_code == 401
    assert COOKIE not in respuesta.cookies


def test_email_repetido_en_dos_cuentas_no_inicia_sesion(
    api, usuario, django_user_model
):
    # Dado un dato heredado con el mismo email en dos cuentas (auth.User no lo impide)
    django_user_model.objects.create_user(
        username="otro", email=EMAIL.upper(), password=CONTRASENA
    )

    # Entonces es ambiguo y se rechaza en lugar de adivinar la cuenta
    assert _login(api).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"password": CONTRASENA},
        {"email": EMAIL},
        {"email": "", "password": CONTRASENA},
        {"email": EMAIL, "password": ""},
        {"email": "no-es-un-correo", "password": CONTRASENA},
    ],
    ids=[
        "vacio",
        "sin-email",
        "sin-password",
        "email-vacio",
        "password-vacia",
        "formato",
    ],
)
def test_payload_incompleto_o_invalido_retorna_400(api, usuario, payload):
    respuesta = api.post(URL, payload, format="json")

    assert respuesta.status_code == 400
    assert COOKIE not in respuesta.cookies


@pytest.mark.parametrize(
    "malicioso",
    ["' OR '1'='1' --", "admin@test.com' --", "'; DROP TABLE auth_user; --"],
)
def test_inyeccion_sql_en_email_o_password_es_rechazada(api, usuario, malicioso):
    por_email = _login(api, email=malicioso)
    por_password = _login(api, password=malicioso)

    assert por_email.status_code in (400, 401)
    assert por_password.status_code == 401


def test_fuerza_bruta_nunca_concede_acceso(api, usuario):
    estados = [_login(api, password=f"intento-{i}").status_code for i in range(10)]

    assert all(estado == 401 for estado in estados)


# --- CORS con credenciales ----------------------------------------------


def test_cors_permite_credenciales_para_que_el_navegador_acepte_la_cookie(api, usuario):
    # Dado el frontend (fetch con credentials: 'include') en su origen
    respuesta = _login(api, HTTP_ORIGIN="http://localhost:5173")

    # Entonces el servidor autoriza el origen con credenciales
    assert respuesta.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert respuesta.headers["Access-Control-Allow-Credentials"] == "true"
