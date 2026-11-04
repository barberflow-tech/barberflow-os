"""SCRUM-29 / HU-06: POST /api/v1/auth/register (registro público de clientes)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.barberias.models import Membresia

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/register"
EMAIL = "nuevo@barberflow.test"
CONTRASENA = "Corte.Fade-2026"


@pytest.fixture
def api():
    return APIClient()


def _registrar(api, **cambios):
    payload = {"email": EMAIL, "password": CONTRASENA}
    payload.update(cambios)
    return api.post(URL, payload, format="json")


def _usuarios():
    return get_user_model().objects.filter(email__iexact=EMAIL)


def test_registro_exitoso_retorna_201_con_hash_y_sin_password(api):
    # Dado un visitante con email y contrasena validos
    # Cuando se registra
    respuesta = _registrar(api)

    # Entonces recibe 201, la contrasena queda con hash y no se devuelve
    assert respuesta.status_code == 201
    usuario = _usuarios().get()
    assert usuario.password != CONTRASENA
    assert usuario.password.startswith("pbkdf2_")
    assert usuario.check_password(CONTRASENA)
    body = respuesta.json()
    assert "password" not in body
    assert CONTRASENA not in respuesta.content.decode()
    assert body["email"] == EMAIL
    assert body["id"] == usuario.pk
    assert body["role"] == "cliente"


def test_registro_crea_cliente_sin_barberia(api):
    # Cuando se registra un visitante
    _registrar(api)

    # Entonces es cliente y no necesita Membresia
    usuario = _usuarios().get()
    assert usuario.perfil.role == "cliente"
    assert not Membresia.objects.filter(user=usuario).exists()


@pytest.mark.parametrize("campo", ["fullName", "full_name"])
def test_registro_acepta_nombre_opcional_del_frontend(api, campo):
    # Dado el payload del formulario, que envia el nombre completo
    respuesta = _registrar(api, **{campo: "Juan Perez"})

    # Entonces se guarda en el perfil
    assert respuesta.status_code == 201
    assert _usuarios().get().perfil.full_name == "Juan Perez"
    assert respuesta.json()["fullName"] == "Juan Perez"


def test_registro_sin_nombre_funciona_con_payload_minimo(api):
    respuesta = _registrar(api)

    assert respuesta.status_code == 201
    assert _usuarios().get().perfil.full_name == ""


def test_registro_acepta_la_ruta_con_barra_final(api):
    respuesta = api.post(
        URL + "/", {"email": EMAIL, "password": CONTRASENA}, format="json"
    )

    assert respuesta.status_code == 201


def test_registro_normaliza_el_email_a_minusculas(api):
    respuesta = _registrar(api, email="  Nuevo@BarberFlow.TEST ")

    assert respuesta.status_code == 201
    assert _usuarios().get().email == EMAIL


def test_email_duplicado_retorna_400(api, django_user_model):
    # Dado un email ya registrado
    django_user_model.objects.create_user(
        username=EMAIL, email=EMAIL, password=CONTRASENA
    )

    # Cuando otro visitante intenta registrarlo, incluso con otras mayusculas
    respuesta = _registrar(api, email=EMAIL.upper())

    # Entonces recibe 400 y no se crea una segunda cuenta
    assert respuesta.status_code == 400
    assert "email" in respuesta.json()
    assert _usuarios().count() == 1


def test_email_duplicado_por_carrera_retorna_400(api, monkeypatch):
    # Dado un registro concurrente que gana justo despues de la validacion
    def _falla(*args, **kwargs):
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(get_user_model().objects.__class__, "create_user", _falla)

    # Entonces el choque contra la restriccion unica se responde 400, no 500
    respuesta = _registrar(api)

    assert respuesta.status_code == 400
    assert "email" in respuesta.json()


@pytest.mark.parametrize("clave_debil", ["123", "password", "12345678", "abc"])
def test_contrasena_debil_retorna_400_y_no_crea_usuario(api, clave_debil):
    respuesta = _registrar(api, password=clave_debil)

    assert respuesta.status_code == 400
    assert "password" in respuesta.json()
    assert not _usuarios().exists()


def test_contrasena_parecida_al_email_retorna_400(api):
    respuesta = _registrar(
        api, email="barberflow2026@correo.test", password="barberflow2026"
    )

    assert respuesta.status_code == 400
    assert "password" in respuesta.json()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"password": CONTRASENA},
        {"email": EMAIL},
        {"email": "no-es-un-correo", "password": CONTRASENA},
        {"email": "", "password": CONTRASENA},
    ],
    ids=["vacio", "sin-email", "sin-password", "email-invalido", "email-vacio"],
)
def test_payload_incompleto_o_invalido_retorna_400(api, payload):
    respuesta = api.post(URL, payload, format="json")

    assert respuesta.status_code == 400
    assert not get_user_model().objects.exists()


@pytest.mark.parametrize("rol", ["admin", "ADMIN", "barbero", "superadmin", ""])
def test_intento_de_crear_admin_se_ignora_y_queda_cliente(api, rol):
    # Dado un visitante que intenta registrarse con un rol privilegiado
    respuesta = _registrar(api, role=rol)

    # Entonces la cuenta se crea siempre como cliente, sin privilegios
    assert respuesta.status_code == 201
    usuario = _usuarios().get()
    assert usuario.perfil.role == "cliente"
    assert usuario.is_staff is False
    assert usuario.is_superuser is False
    assert respuesta.json()["role"] == "cliente"


def test_intento_de_enviar_is_staff_e_is_superuser_se_ignora(api):
    respuesta = _registrar(api, is_staff=True, is_superuser=True, is_active=False)

    assert respuesta.status_code == 201
    usuario = _usuarios().get()
    assert usuario.is_staff is False
    assert usuario.is_superuser is False
    assert usuario.is_active is True


def test_registro_ignora_un_token_invalido_en_la_cabecera(api):
    # Dado un navegador con un access token vencido
    api.credentials(HTTP_AUTHORIZATION="Bearer token-vencido")

    # Entonces el registro publico igual funciona
    assert _registrar(api).status_code == 201


def test_registro_solo_acepta_post(api):
    assert api.get(URL).status_code == 405
