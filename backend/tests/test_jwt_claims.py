"""SCRUM-29 / HU-06: claims personalizados del JWT (user_id, email, role)."""

from datetime import timedelta

import jwt
import pytest
from django.conf import settings as django_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.barberias.models import Membresia
from apps.usuarios.models import PerfilUsuario, rol_de
from apps.usuarios.tokens import LoginTokenSerializer, RefreshTokenSerializer

pytestmark = pytest.mark.django_db

EMAIL = "ana@barberflow.test"
CONTRASENA = "Corte.Fade-2026"
CLAIMS_ESTANDAR = {"token_type", "exp", "iat", "jti"}


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user(
        username=EMAIL, email=EMAIL, password=CONTRASENA
    )


def _con_rol(usuario, rol):
    usuario.perfil.role = rol
    usuario.perfil.save()
    return usuario


def _refrescar(refresh):
    serializer = RefreshTokenSerializer(data={"refresh": str(refresh)})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# --- Claims del par de tokens -------------------------------------------


@pytest.mark.parametrize("rol", ["cliente", "barbero", "admin"])
def test_el_token_incluye_user_id_email_y_role(usuario, rol):
    # Dado un usuario con un rol
    _con_rol(usuario, rol)

    # Cuando se emite su par de tokens
    refresh = LoginTokenSerializer.get_token(usuario)
    access = refresh.access_token

    # Entonces ambos llevan user_id (entero), email y role en minusculas
    for token in (access, refresh):
        assert token["user_id"] == usuario.pk
        assert isinstance(token["user_id"], int)
        assert token["email"] == EMAIL
        assert token["role"] == rol


def test_el_token_solo_lleva_los_claims_esperados(usuario):
    # Entonces no se filtran datos sensibles ni privilegios dentro del token
    payload = LoginTokenSerializer.get_token(usuario).access_token.payload

    assert set(payload) - CLAIMS_ESTANDAR == {"user_id", "email", "role"}
    assert "password" not in payload
    assert "is_staff" not in payload
    assert "is_superuser" not in payload


def test_cliente_sin_barberia_recibe_role_cliente(usuario):
    # Dado un cliente sin Membresia
    assert not Membresia.objects.filter(user=usuario).exists()

    # Entonces el token lo identifica como cliente
    assert LoginTokenSerializer.get_token(usuario).access_token["role"] == "cliente"


def test_usuario_sin_perfil_recibe_el_rol_de_menor_privilegio(usuario):
    # Dado un usuario cuyo perfil no existe
    PerfilUsuario.objects.filter(user=usuario).delete()
    usuario.refresh_from_db()

    # Entonces el token no concede mas que cliente
    assert LoginTokenSerializer.get_token(usuario).access_token["role"] == "cliente"


def test_el_login_con_el_serializer_entrega_access_y_refresh_con_claims(usuario):
    # Dado un usuario con credenciales validas
    _con_rol(usuario, "barbero")
    serializer = LoginTokenSerializer(data={"username": EMAIL, "password": CONTRASENA})

    # Cuando se validan las credenciales
    assert serializer.is_valid()

    # Entonces ambos tokens decodifican con los claims del usuario
    datos = serializer.validated_data
    for token in (AccessToken(datos["access"]), RefreshToken(datos["refresh"])):
        assert token["user_id"] == usuario.pk
        assert token["email"] == EMAIL
        assert token["role"] == "barbero"


def test_credenciales_invalidas_no_emiten_token(usuario):
    serializer = LoginTokenSerializer(
        data={"username": EMAIL, "password": "incorrecta"}
    )

    with pytest.raises(AuthenticationFailed):
        serializer.is_valid(raise_exception=True)


# --- Firma ---------------------------------------------------------------


def test_un_token_con_claims_alterados_y_otra_firma_es_rechazado(usuario):
    # Dado un atacante que reescribe el rol y firma con otra clave
    payload = dict(LoginTokenSerializer.get_token(usuario).access_token.payload)
    payload["role"] = "admin"
    forjado = jwt.encode(payload, "otra-clave", algorithm="HS256")

    # Entonces la verificacion de SimpleJWT lo rechaza
    with pytest.raises(TokenError):
        AccessToken(forjado)


def test_el_token_alterado_en_el_payload_sin_refirmar_es_rechazado(usuario):
    # Dado un token valido al que se le cambia el payload pero no la firma
    token = str(LoginTokenSerializer.get_token(usuario).access_token)
    cabecera, _, firma = token.split(".")
    otro = jwt.encode({"role": "admin"}, "x", algorithm="HS256").split(".")[1]

    with pytest.raises(TokenError):
        AccessToken(f"{cabecera}.{otro}.{firma}")


# --- Refresh -------------------------------------------------------------


def test_el_refresh_entrega_un_access_con_los_mismos_claims(usuario):
    # Dado un refresh token emitido en el login
    _con_rol(usuario, "barbero")
    refresh = LoginTokenSerializer.get_token(usuario)

    # Cuando se renueva
    access = AccessToken(_refrescar(refresh)["access"])

    # Entonces el access nuevo conserva user_id, email y role
    assert access["user_id"] == usuario.pk
    assert access["email"] == EMAIL
    assert access["role"] == "barbero"


def test_el_refresh_toma_el_rol_vigente_y_no_el_del_login(usuario):
    # Dado un refresh emitido cuando el usuario era cliente
    refresh = LoginTokenSerializer.get_token(usuario)
    assert refresh["role"] == "cliente"

    # Cuando un admin lo asciende a barbero y luego se renueva el access
    _con_rol(usuario, "barbero")
    access = AccessToken(_refrescar(refresh)["access"])

    # Entonces el access nuevo ya trae el rol actual
    assert access["role"] == "barbero"


def test_el_refresh_toma_el_email_vigente(usuario):
    refresh = LoginTokenSerializer.get_token(usuario)
    usuario.email = "nuevo@barberflow.test"
    usuario.save()

    assert (
        AccessToken(_refrescar(refresh)["access"])["email"] == "nuevo@barberflow.test"
    )


def test_el_access_renovado_conserva_la_vigencia_del_original(usuario):
    refresh = LoginTokenSerializer.get_token(usuario)
    original = refresh.access_token

    renovado = AccessToken(_refrescar(refresh)["access"])

    # Mismo origen de tiempo: el exp no se alarga por el re-firmado de claims
    assert abs(renovado["exp"] - original["exp"]) <= 2


def test_el_refresh_de_un_usuario_inactivo_es_rechazado(usuario):
    refresh = LoginTokenSerializer.get_token(usuario)
    usuario.is_active = False
    usuario.save()

    with pytest.raises(AuthenticationFailed):
        _refrescar(refresh)


def test_el_refresh_de_un_usuario_borrado_es_401_y_no_500(usuario):
    refresh = LoginTokenSerializer.get_token(usuario)
    usuario.delete()

    with pytest.raises(AuthenticationFailed):
        _refrescar(refresh)


def test_el_refresh_invalido_es_rechazado():
    serializer = RefreshTokenSerializer(data={"refresh": "token-alterado"})

    with pytest.raises(TokenError):
        serializer.is_valid(raise_exception=True)


def test_un_access_token_no_sirve_como_refresh(usuario):
    access = LoginTokenSerializer.get_token(usuario).access_token

    with pytest.raises(TokenError):
        _refrescar(access)


def test_con_rotacion_el_nuevo_refresh_tambien_lleva_claims(usuario, monkeypatch):
    # Dado un despliegue que activa la rotacion de refresh tokens
    monkeypatch.setattr(api_settings, "ROTATE_REFRESH_TOKENS", True)
    _con_rol(usuario, "admin")
    refresh = LoginTokenSerializer.get_token(usuario)

    datos = _refrescar(refresh)

    # Entonces access y refresh rotado conservan los claims
    for token in (AccessToken(datos["access"]), RefreshToken(datos["refresh"])):
        assert token["user_id"] == usuario.pk
        assert token["email"] == EMAIL
        assert token["role"] == "admin"


# --- Configuracion SimpleJWT e infraestructura de permisos ---------------


def test_la_configuracion_usa_los_serializers_personalizados():
    assert api_settings.TOKEN_OBTAIN_SERIALIZER == (
        "apps.usuarios.tokens.LoginTokenSerializer"
    )
    assert api_settings.TOKEN_REFRESH_SERIALIZER == (
        "apps.usuarios.tokens.RefreshTokenSerializer"
    )
    assert api_settings.USER_ID_CLAIM == "user_id"
    assert api_settings.USER_ID_FIELD == "id"
    assert api_settings.ALGORITHM == "HS256"
    assert api_settings.SIGNING_KEY == django_settings.SECRET_KEY


def test_el_access_dura_menos_que_el_refresh():
    assert timedelta(0) < api_settings.ACCESS_TOKEN_LIFETIME
    assert api_settings.ACCESS_TOKEN_LIFETIME < api_settings.REFRESH_TOKEN_LIFETIME


def test_jwt_authentication_resuelve_el_usuario_y_el_claim_coincide_con_la_base(
    usuario,
):
    # Dado un access token en la cabecera Authorization
    _con_rol(usuario, "barbero")
    access = LoginTokenSerializer.get_token(usuario).access_token
    request = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {access}")

    # Cuando DRF autentica la peticion
    user, token = JWTAuthentication().authenticate(request)

    # Entonces el usuario es el del token y el rol del claim coincide con rol_de(),
    # que es lo que deben consultar los permisos (HasRole) para decidir
    assert user.pk == usuario.pk
    assert token["role"] == rol_de(user) == "barbero"
