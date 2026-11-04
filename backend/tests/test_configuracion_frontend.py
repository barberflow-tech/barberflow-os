"""Configuracion que el frontend necesita: DRF, SimpleJWT, CORS y cookie del refresh.

El frontend (React en otro origen) llama con fetch(..., {credentials: "include"}):
sin CORS con credenciales o con una cookie mal configurada, el navegador
descarta la cookie del refresh y la sesion no se puede restaurar.
"""

import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings

from apps.usuarios.permissions import OrigenPermitido
from apps.usuarios.views import LoginView, RefreshView, RegistroView

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = "http://localhost:5173"
CONTRASENA = "Corte.Fade-2026"


def _settings_con_entorno(**entorno):
    """Importa config.settings en un proceso aparte con ese entorno.

    Devuelve (codigo_de_salida, valores_de_settings | stderr). Es la unica forma
    fiable de probar la configuracion que se decide al importar el modulo.
    """
    codigo = (
        "import json, django.conf as c; s = c.settings;"
        "print(json.dumps({'cookie': s.AUTH_REFRESH_COOKIE,"
        " 'hosts': s.ALLOWED_HOSTS, 'origins': s.CORS_ALLOWED_ORIGINS,"
        " 'creds': s.CORS_ALLOW_CREDENTIALS,"
        " 'access': s.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),"
        " 'refresh': s.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()}))"
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("AUTH_", "DJANGO_", "CORS_", "JWT_"))
    }
    env.update(DJANGO_SETTINGS_MODULE="config.settings", **entorno)
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        return resultado.returncode, resultado.stderr
    return 0, json.loads(resultado.stdout)


# --- DRF -----------------------------------------------------------------


def test_drf_solo_autentica_con_jwt_y_exige_login_por_defecto():
    # Sin SessionAuthentication no hay cookie de sesion ni CSRF en la API
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    )
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == (
        "rest_framework.permissions.IsAuthenticated",
    )
    vista = APIView()
    assert [type(a) for a in vista.get_authenticators()] == [JWTAuthentication]
    assert [type(p) for p in vista.get_permissions()] == [IsAuthenticated]


@pytest.mark.parametrize(
    ("vista", "permiso"),
    [(RegistroView, AllowAny), (LoginView, AllowAny), (RefreshView, OrigenPermitido)],
)
def test_los_endpoints_publicos_de_auth_lo_declaran_explicitamente(vista, permiso):
    # Son publicos a proposito y no heredan JWT: un access vencido en el
    # navegador no debe impedir registrarse, iniciar sesion ni renovar
    assert vista.authentication_classes == []
    assert vista.permission_classes == [permiso]


@pytest.mark.django_db
def test_un_endpoint_de_negocio_sigue_exigiendo_autenticacion():
    assert APIClient().get("/api/v1/barbers/me/portfolio").status_code == 401


# --- SimpleJWT -----------------------------------------------------------


def test_simplejwt_firma_con_la_clave_del_proyecto_y_usa_bearer():
    assert api_settings.ALGORITHM == "HS256"
    assert api_settings.SIGNING_KEY == settings.SECRET_KEY
    assert api_settings.AUTH_HEADER_TYPES == ("Bearer",)
    assert api_settings.USER_ID_CLAIM == "user_id"


def test_el_access_dura_lo_suficiente_para_una_sesion_sin_renovacion_automatica():
    # El frontend solo renueva al cargar la app: un access de pocos minutos
    # cerraria la sesion a media tarea
    assert api_settings.ACCESS_TOKEN_LIFETIME >= timedelta(minutes=15)
    assert api_settings.REFRESH_TOKEN_LIFETIME > api_settings.ACCESS_TOKEN_LIFETIME


def test_la_vida_de_los_tokens_se_configura_por_entorno():
    codigo, valores = _settings_con_entorno(
        DJANGO_DEBUG="True", JWT_ACCESS_MINUTES="30", JWT_REFRESH_DAYS="3"
    )

    assert codigo == 0
    assert valores["access"] == 30 * 60
    assert valores["refresh"] == 3 * 24 * 3600


# --- CORS ----------------------------------------------------------------


def test_cors_permite_credenciales_y_no_usa_comodines():
    # Con credentials: "include" el navegador exige un origen explicito
    assert settings.CORS_ALLOW_CREDENTIALS is True
    assert "*" not in settings.CORS_ALLOWED_ORIGINS
    assert not getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
    assert all(
        o.startswith(("http://", "https://")) for o in settings.CORS_ALLOWED_ORIGINS
    )


def test_el_origen_del_frontend_local_esta_autorizado_por_defecto():
    codigo, valores = _settings_con_entorno(DJANGO_DEBUG="True")

    assert codigo == 0
    assert valores["origins"] == [FRONTEND]
    assert valores["creds"] is True


def test_los_origenes_cors_se_configuran_por_entorno():
    codigo, valores = _settings_con_entorno(
        CORS_ALLOWED_ORIGINS=" https://app.vercel.app , http://localhost:5173 ,"
    )

    assert codigo == 0
    assert valores["origins"] == ["https://app.vercel.app", "http://localhost:5173"]


def test_la_configuracion_cors_pasa_las_comprobaciones_de_django():
    call_command("check")  # corsheaders valida esquema y formato de los origenes


@pytest.mark.django_db
def test_el_preflight_del_login_autoriza_al_frontend_con_credenciales():
    # fetch con Content-Type: application/json dispara un preflight OPTIONS
    response = APIClient().options(
        "/api/v1/auth/login",
        HTTP_ORIGIN=FRONTEND,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "content-type" in response.headers["Access-Control-Allow-Headers"]


@pytest.mark.django_db
def test_el_preflight_permite_enviar_el_access_en_authorization():
    response = APIClient().options(
        "/api/v1/appointments",
        HTTP_ORIGIN=FRONTEND,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )

    assert "authorization" in response.headers["Access-Control-Allow-Headers"]


@pytest.mark.django_db
def test_un_origen_ajeno_no_recibe_cabeceras_cors():
    response = APIClient().options(
        "/api/v1/auth/login",
        HTTP_ORIGIN="https://sitio-malicioso.example",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )

    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers


@pytest.mark.django_db
def test_login_y_refresh_responden_con_credenciales_cors_al_frontend(
    django_user_model,
):
    # Flujo del navegador: login, y luego restoreSession con la cookie
    django_user_model.objects.create_user(
        username="a@test.com", email="a@test.com", password=CONTRASENA
    )
    api = APIClient()

    login = api.post(
        "/api/v1/auth/login",
        {"email": "a@test.com", "password": CONTRASENA},
        format="json",
        HTTP_ORIGIN=FRONTEND,
    )
    refresh = api.post("/api/v1/auth/refresh", HTTP_ORIGIN=FRONTEND)

    for response in (login, refresh):
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
        assert response.headers["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.django_db
def test_el_error_401_del_refresh_tambien_lleva_cors_para_que_el_frontend_lo_lea():
    # Si faltara, el navegador ocultaria el 401 y restoreSession veria un error de red
    response = APIClient().post("/api/v1/auth/refresh", HTTP_ORIGIN=FRONTEND)

    assert response.status_code == 401
    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


# --- Hosts permitidos ----------------------------------------------------


def test_los_hosts_permitidos_se_configuran_por_entorno():
    codigo, valores = _settings_con_entorno(
        DJANGO_ALLOWED_HOSTS=" api.barberflow.co , barberflow-api.onrender.com ,"
    )

    assert codigo == 0
    assert valores["hosts"] == ["api.barberflow.co", "barberflow-api.onrender.com"]


def test_sin_hosts_configurados_la_lista_queda_vacia():
    # Django solo admite localhost con DEBUG; fuera de DEBUG hay que configurarlos
    codigo, valores = _settings_con_entorno()

    assert codigo == 0
    assert valores["hosts"] == []


# --- Cookie del refresh: desarrollo vs produccion -----------------------


def test_cookie_en_desarrollo_es_lax_y_sin_secure():
    # localhost:5173 y localhost:5000 son el mismo sitio: Lax basta y no hace
    # falta HTTPS
    codigo, valores = _settings_con_entorno(DJANGO_DEBUG="True")

    assert codigo == 0
    assert valores["cookie"] == {
        "NAME": "refresh_token",
        "PATH": "/api/v1/auth/",
        "SECURE": False,
        "SAMESITE": "Lax",
    }


def test_cookie_fuera_de_debug_es_secure_por_defecto():
    codigo, valores = _settings_con_entorno(DJANGO_DEBUG="False")

    assert codigo == 0
    assert valores["cookie"]["SECURE"] is True
    assert valores["cookie"]["SAMESITE"] == "Lax"


def test_cookie_cross_site_de_produccion_es_none_y_secure():
    # Frontend en Vercel y API en Render son sitios distintos
    codigo, valores = _settings_con_entorno(
        DJANGO_DEBUG="False", AUTH_COOKIE_SAMESITE="None", AUTH_COOKIE_SECURE="True"
    )

    assert codigo == 0
    assert valores["cookie"]["SAMESITE"] == "None"
    assert valores["cookie"]["SECURE"] is True


@pytest.mark.parametrize(
    "entorno",
    [
        {"AUTH_COOKIE_SAMESITE": "None", "AUTH_COOKIE_SECURE": "False"},
        {"AUTH_COOKIE_SAMESITE": "None", "DJANGO_DEBUG": "True"},
        {"AUTH_COOKIE_SAMESITE": "Bogus"},
        {"AUTH_COOKIE_SAMESITE": "lax"},
    ],
    ids=["none-sin-secure", "none-en-debug", "valor-inventado", "minusculas"],
)
def test_una_cookie_que_el_navegador_rechazaria_impide_arrancar(entorno):
    codigo, error = _settings_con_entorno(**entorno)

    assert codigo != 0
    assert "ImproperlyConfigured" in error


@pytest.mark.django_db
def test_la_cookie_no_fija_dominio_y_queda_ligada_al_host_de_la_api(django_user_model):
    # Sin Domain, el navegador la guarda solo para el host que la emitio y no
    # la comparte con otros subdominios
    assert "DOMAIN" not in settings.AUTH_REFRESH_COOKIE
    django_user_model.objects.create_user(
        username="a@test.com", email="a@test.com", password=CONTRASENA
    )
    response = APIClient().post(
        "/api/v1/auth/login",
        {"email": "a@test.com", "password": CONTRASENA},
        format="json",
    )

    assert not response.cookies["refresh_token"]["domain"]
