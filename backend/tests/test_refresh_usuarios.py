"""SCRUM-29 / HU-06: POST /api/v1/auth/refresh (refresh token solo por cookie)."""

from datetime import timedelta

import jwt
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.usuarios.models import Rol

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
URL = "/api/v1/auth/refresh"
EMAIL = "user@test.com"
CONTRASENA = "Corte.Fade-2026"
COOKIE = "refresh_token"
ORIGEN = "http://localhost:5173"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user(
        username=EMAIL, email=EMAIL, password=CONTRASENA
    )


@pytest.fixture
def sesion(api, usuario):
    """Cliente que ya inicio sesion: su cookie de refresh queda en api.cookies."""
    respuesta = api.post(LOGIN, {"email": EMAIL, "password": CONTRASENA}, format="json")
    assert respuesta.status_code == 200
    return api


def _cookie_borrada(respuesta):
    cookie = respuesta.cookies[COOKIE]
    assert cookie.value == ""
    assert int(cookie["max-age"]) == 0
    assert cookie["path"] == "/api/v1/auth/"
    assert cookie["httponly"] is True


def _refresh(api, **extra):
    return api.post(URL, **extra)


# --- Refresh correcto ----------------------------------------------------


def test_refresh_con_cookie_valida_retorna_access_nuevo_y_usuario(sesion, usuario):
    # Dado un cliente con sesion iniciada (cookie HttpOnly en el navegador)
    acceso_original = sesion.post(
        LOGIN, {"email": EMAIL, "password": CONTRASENA}, format="json"
    ).json()["access"]

    # Cuando pide renovar la sesion, sin enviar nada en el cuerpo
    respuesta = _refresh(sesion)

    # Entonces recibe un access nuevo y los datos del usuario
    assert respuesta.status_code == 200
    body = respuesta.json()
    assert set(body) == {"access", "user"}
    assert body["user"] == {"id": usuario.pk, "email": EMAIL, "role": "cliente"}
    assert body["access"] != acceso_original
    access = AccessToken(body["access"])
    assert access["user_id"] == usuario.pk
    assert access["email"] == EMAIL
    assert access["role"] == "cliente"


def test_refresh_no_devuelve_el_refresh_token_en_el_cuerpo(sesion):
    respuesta = _refresh(sesion)

    assert "refresh" not in respuesta.json()
    assert "refresh" not in respuesta.json()["user"]
    assert sesion.cookies[COOKIE].value not in respuesta.content.decode()


def test_refresh_sin_rotacion_no_vuelve_a_enviar_la_cookie(sesion):
    assert COOKIE not in _refresh(sesion).cookies


def test_la_respuesta_con_tokens_no_se_guarda_en_cache(sesion):
    assert _refresh(sesion).headers["Cache-Control"] == "no-store"


def test_refresh_se_puede_repetir_con_la_misma_cookie(sesion):
    assert _refresh(sesion).status_code == 200
    assert _refresh(sesion).status_code == 200


def test_refresh_toma_el_rol_vigente_y_no_el_del_login(sesion, usuario):
    # Dado un cliente que luego es ascendido a barbero
    usuario.perfil.role = Rol.BARBERO
    usuario.perfil.save()

    respuesta = _refresh(sesion)

    # Entonces el access y el usuario reflejan el rol actual
    assert respuesta.json()["user"]["role"] == "barbero"
    assert AccessToken(respuesta.json()["access"])["role"] == "barbero"


def test_refresh_toma_el_email_vigente(sesion, usuario):
    usuario.email = "otro@test.com"
    usuario.save()

    respuesta = _refresh(sesion)

    assert respuesta.json()["user"]["email"] == "otro@test.com"
    assert AccessToken(respuesta.json()["access"])["email"] == "otro@test.com"


def test_refresh_acepta_la_ruta_con_barra_final(sesion):
    assert sesion.post(URL + "/").status_code == 200


def test_refresh_ignora_un_access_token_vencido_en_la_cabecera(sesion):
    sesion.credentials(HTTP_AUTHORIZATION="Bearer token-vencido")

    assert _refresh(sesion).status_code == 200


def test_refresh_solo_acepta_post(sesion):
    assert sesion.get(URL).status_code == 405


# --- La cookie es la unica fuente del refresh token ----------------------


def test_no_acepta_el_refresh_token_en_el_cuerpo(api, usuario):
    # Dado un refresh token valido enviado en el cuerpo, sin cookie
    refresh = str(RefreshToken.for_user(usuario))

    respuesta = api.post(URL, {"refresh": refresh}, format="json")

    # Entonces se rechaza: solo vale la cookie
    assert respuesta.status_code == 401
    assert "access" not in respuesta.json()


def test_no_acepta_el_refresh_token_en_la_query_string(api, usuario):
    refresh = str(RefreshToken.for_user(usuario))

    assert api.post(f"{URL}?refresh={refresh}").status_code == 401


def test_no_acepta_el_refresh_token_en_una_cabecera(api, usuario):
    refresh = str(RefreshToken.for_user(usuario))

    respuesta = api.post(URL, HTTP_AUTHORIZATION=f"Bearer {refresh}")

    assert respuesta.status_code == 401


def test_el_cuerpo_se_ignora_aunque_haya_cookie_valida(sesion):
    # Dado un cuerpo con un refresh falso y una cookie valida
    respuesta = sesion.post(URL, {"refresh": "falso"}, format="json")

    # Entonces se usa la cookie
    assert respuesta.status_code == 200


def test_un_refresh_valido_en_el_cuerpo_no_rescata_una_cookie_invalida(api, usuario):
    api.cookies[COOKIE] = "token-alterado"
    refresh = str(RefreshToken.for_user(usuario))

    respuesta = api.post(URL, {"refresh": refresh}, format="json")

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


# --- Errores: 401 y la cookie se elimina ---------------------------------


def test_sin_cookie_retorna_401_y_elimina_la_cookie(api):
    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    assert "access" not in respuesta.json()
    _cookie_borrada(respuesta)


def test_cookie_vacia_retorna_401_y_elimina_la_cookie(api):
    api.cookies[COOKIE] = ""

    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_cookie_invalida_retorna_401_y_elimina_la_cookie(api):
    api.cookies[COOKIE] = "esto-no-es-un-jwt"

    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_cookie_con_la_firma_alterada_retorna_401_y_elimina_la_cookie(sesion):
    valido = sesion.cookies[COOKIE].value
    sesion.cookies[COOKIE] = valido[:-4] + ("AAAA" if valido[-4:] != "AAAA" else "BBBB")

    respuesta = _refresh(sesion)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_cookie_con_el_payload_alterado_retorna_401_y_elimina_la_cookie(sesion):
    cabecera, _, firma = sesion.cookies[COOKIE].value.split(".")
    payload = jwt.encode({"role": "admin"}, "x" * 32, algorithm="HS256").split(".")[1]
    sesion.cookies[COOKIE] = f"{cabecera}.{payload}.{firma}"

    respuesta = _refresh(sesion)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_cookie_firmada_con_otra_clave_retorna_401(api, usuario):
    payload = dict(RefreshToken.for_user(usuario).payload)
    api.cookies[COOKIE] = jwt.encode(payload, "otra-clave" * 4, algorithm="HS256")

    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_cookie_expirada_retorna_401_y_elimina_la_cookie(api, usuario):
    # Dado un refresh token que ya vencio
    refresh = RefreshToken.for_user(usuario)
    refresh.set_exp(lifetime=-timedelta(seconds=1))
    api.cookies[COOKIE] = str(refresh)

    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_un_access_token_en_la_cookie_no_sirve_como_refresh(api, usuario):
    api.cookies[COOKIE] = str(RefreshToken.for_user(usuario).access_token)

    respuesta = _refresh(api)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_usuario_inactivo_retorna_401_y_elimina_la_cookie(sesion, usuario):
    usuario.is_active = False
    usuario.save()

    respuesta = _refresh(sesion)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_usuario_borrado_retorna_401_y_no_500(sesion, usuario):
    usuario.delete()

    respuesta = _refresh(sesion)

    assert respuesta.status_code == 401
    _cookie_borrada(respuesta)


def test_el_mensaje_de_error_es_generico(api):
    # No revela por que fallo: cookie ausente, vencida o alterada dan lo mismo
    ausente = _refresh(api).json()
    api.cookies[COOKIE] = "esto-no-es-un-jwt"
    invalida = _refresh(api).json()

    assert ausente == invalida


# --- Rotacion de refresh tokens -----------------------------------------


def test_con_rotacion_la_cookie_se_reemplaza_y_el_cuerpo_sigue_sin_refresh(
    sesion, usuario, monkeypatch
):
    # Dado un despliegue que activa la rotacion de refresh tokens
    monkeypatch.setattr(api_settings, "ROTATE_REFRESH_TOKENS", True)
    anterior = sesion.cookies[COOKIE].value

    respuesta = _refresh(sesion)

    # Entonces el refresh nuevo viaja solo en la cookie, con los mismos atributos
    assert respuesta.status_code == 200
    assert "refresh" not in respuesta.json()
    nueva = respuesta.cookies[COOKIE]
    assert nueva.value and nueva.value != anterior
    assert nueva["httponly"] is True
    assert nueva["path"] == "/api/v1/auth/"
    assert nueva["samesite"] == "Lax"
    assert int(nueva["max-age"]) == int(
        api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()
    )
    assert nueva.value not in respuesta.content.decode()
    refresh = RefreshToken(nueva.value)
    assert refresh["user_id"] == usuario.pk
    assert refresh["role"] == "cliente"


# --- Origen (defensa CSRF para la cookie) --------------------------------


def test_origen_permitido_recibe_credenciales_cors(sesion):
    respuesta = _refresh(sesion, HTTP_ORIGIN=ORIGEN)

    assert respuesta.status_code == 200
    assert respuesta.headers["Access-Control-Allow-Origin"] == ORIGEN
    assert respuesta.headers["Access-Control-Allow-Credentials"] == "true"


def test_origen_ajeno_retorna_403_sin_renovar_ni_borrar_la_cookie(sesion):
    # Dado una pagina de otro sitio que dispara el refresh con la cookie de la victima
    respuesta = _refresh(sesion, HTTP_ORIGIN="https://sitio-malicioso.example")

    # Entonces se rechaza, no entrega access y no cierra la sesion de la victima
    assert respuesta.status_code == 403
    assert "access" not in respuesta.json()
    assert COOKIE not in respuesta.cookies


def test_origen_nulo_retorna_403(sesion):
    assert _refresh(sesion, HTTP_ORIGIN="null").status_code == 403


def test_sin_cabecera_origin_se_permite(sesion):
    # Clientes que no son navegadores (curl, pruebas) no envian Origin
    assert _refresh(sesion).status_code == 200


# --- Cookie de borrado en produccion ------------------------------------


def test_borrar_la_cookie_cross_site_incluye_secure_y_samesite_none(api, settings):
    # Dado el despliegue Vercel + Render (SameSite=None; Secure)
    settings.AUTH_REFRESH_COOKIE = {
        **settings.AUTH_REFRESH_COOKIE,
        "SAMESITE": "None",
        "SECURE": True,
    }

    respuesta = _refresh(api)

    # Entonces el Set-Cookie de borrado lleva los mismos atributos que el de
    # creacion; sin Secure los navegadores rechazan SameSite=None
    cookie = respuesta.cookies[COOKIE]
    assert respuesta.status_code == 401
    assert cookie["samesite"] == "None"
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["path"] == "/api/v1/auth/"


def test_el_nombre_de_la_cookie_configurado_es_el_que_se_lee(api, usuario, settings):
    settings.AUTH_REFRESH_COOKIE = {**settings.AUTH_REFRESH_COOKIE, "NAME": "rt"}
    api.cookies["rt"] = str(RefreshToken.for_user(usuario))

    assert _refresh(api).status_code == 200
    # y la cookie con el nombre por defecto ya no es la fuente
    api.cookies.clear()
    api.cookies[COOKIE] = "x"
    assert _refresh(api).status_code == 401
