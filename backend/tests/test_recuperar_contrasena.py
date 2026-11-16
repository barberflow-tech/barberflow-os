"""HU-06: recuperacion de contrasena (POST /auth/password-reset y /confirm) por correo SMTP."""

import re
import smtplib
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from rest_framework.test import APIClient

from apps.usuarios import correo

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/password-reset"
URL_CONFIRMAR = "/api/v1/auth/password-reset/confirm"
URL_LOGIN = "/api/v1/auth/login"
EMAIL = "ana@barberflow.test"
ANTIGUA = "Corte.Fade-2026"
NUEVA = "Navaja.Dorada-2027"
ENLACE = "http://x/restablecer?uid=1&token=2"


@pytest.fixture(autouse=True)
def _limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(
        username=EMAIL, email=EMAIL, password=ANTIGUA
    )


@pytest.fixture
def enviados(settings):
    """Intercepta el envio real y devuelve la lista de (destino, enlace)."""
    settings.FRONTEND_URL = "http://localhost:5173"
    lista = []
    with mock.patch(
        "apps.usuarios.views.enviar_recuperacion_contrasena",
        side_effect=lambda destino, enlace, minutos: lista.append((destino, enlace)),
    ):
        yield lista


def _credenciales(enlace):
    uid, token = re.search(r"uid=([^&]+)&token=(.+)$", enlace).groups()
    return uid, token


def _pedir(api, email=EMAIL):
    return api.post(URL, {"email": email}, format="json")


def _confirmar(api, uid, token, password):
    return api.post(
        URL_CONFIRMAR, {"uid": uid, "token": token, "password": password}, format="json"
    )


def test_solicitud_de_cuenta_existente_envia_el_enlace(api, usuario, enviados):
    respuesta = _pedir(api)

    assert respuesta.status_code == 202
    assert len(enviados) == 1
    destino, enlace = enviados[0]
    assert destino == EMAIL
    assert enlace.startswith("http://localhost:5173/restablecer?uid=")


def test_correo_inexistente_responde_igual_y_no_envia(api, usuario, enviados):
    existente = _pedir(api)
    cache.clear()
    inexistente = _pedir(api, "nadie@barberflow.test")

    assert inexistente.status_code == existente.status_code == 202
    assert inexistente.json() == existente.json()
    assert len(enviados) == 1  # solo el de la cuenta real


def test_correo_se_busca_sin_distinguir_mayusculas(api, usuario, enviados):
    _pedir(api, EMAIL.upper())
    assert len(enviados) == 1


def test_cuenta_inactiva_no_recibe_correo(api, usuario, enviados):
    usuario.is_active = False
    usuario.save()
    assert _pedir(api).status_code == 202
    assert enviados == []


def test_email_mal_formado_da_400(api, enviados):
    assert _pedir(api, "no-es-correo").status_code == 400
    assert enviados == []


def test_solicitud_limitada_a_5_por_hora(api, usuario, enviados):
    codigos = [_pedir(api).status_code for _ in range(6)]
    assert codigos == [202] * 5 + [429]


def test_restablecer_cambia_la_contrasena_y_permite_entrar(api, usuario, enviados):
    _pedir(api)
    uid, token = _credenciales(enviados[0][1])

    assert _confirmar(api, uid, token, NUEVA).status_code == 200

    nueva = api.post(URL_LOGIN, {"email": EMAIL, "password": NUEVA}, format="json")
    vieja = api.post(URL_LOGIN, {"email": EMAIL, "password": ANTIGUA}, format="json")
    assert nueva.status_code == 200
    assert vieja.status_code == 401


def test_el_enlace_solo_sirve_una_vez(api, usuario, enviados):
    _pedir(api)
    uid, token = _credenciales(enviados[0][1])

    assert _confirmar(api, uid, token, NUEVA).status_code == 200
    assert _confirmar(api, uid, token, "Otra.Clave-2028").status_code == 400


def test_token_alterado_o_uid_invalido_da_400(api, usuario, enviados):
    _pedir(api)
    uid, token = _credenciales(enviados[0][1])

    malo = _confirmar(api, uid, token + "x", NUEVA)
    basura = _confirmar(api, "!!!", token, NUEVA)

    assert malo.status_code == basura.status_code == 400
    assert malo.json() == basura.json()  # mismo mensaje: no revela cual fallo


def test_contrasena_debil_da_400_y_no_gasta_el_enlace(api, usuario, enviados):
    _pedir(api)
    uid, token = _credenciales(enviados[0][1])

    debil = _confirmar(api, uid, token, "12345678")
    assert debil.status_code == 400
    assert "password" in debil.json()

    assert _confirmar(api, uid, token, NUEVA).status_code == 200


# --- correo.py: envio con el backend de correo de Django -------------------------


def test_enviar_correo_entrega_texto_y_html(settings, mailoutbox):
    settings.DEFAULT_FROM_EMAIL = "BarberFlow <hola@barberflow.test>"

    assert correo.enviar_correo("a@b.co", "Asunto", "<p>x</p>", "x") is True

    assert len(mailoutbox) == 1
    mensaje = mailoutbox[0]
    assert mensaje.to == ["a@b.co"]
    assert mensaje.subject == "Asunto"
    assert mensaje.from_email == "BarberFlow <hola@barberflow.test>"
    assert mensaje.body == "x"
    assert mensaje.alternatives[0][0] == "<p>x</p>"


def test_fallo_del_servidor_de_correo_se_traga_y_devuelve_false():
    for error in (
        smtplib.SMTPAuthenticationError(535, b"mal"),
        ConnectionRefusedError(),
    ):
        with mock.patch.object(EmailMultiAlternatives, "send", side_effect=error):
            assert correo.enviar_correo("a@b.co", "A", "h", "t") is False


def test_el_correo_de_recuperacion_incluye_el_enlace(mailoutbox):
    assert correo.enviar_recuperacion_contrasena("a@b.co", ENLACE, 30) is True

    mensaje = mailoutbox[0]
    assert ENLACE in mensaje.body
    assert ENLACE in mensaje.alternatives[0][0]
    assert "30 minutos" in mensaje.body
