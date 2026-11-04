"""JWT con claims propios: user_id, email y role (HU-06).

Aqui se escriben user_id (como entero), email y role, tanto en el refresh
como en el access: RefreshToken.access_token copia todos los claims del
refresh.

El claim `role` sirve para que el frontend redirija segun el rol. Los permisos
del backend (HasRole) deben decidir con rol_de(request.user), que lee la base:
un rol cambiado no debe seguir vigente hasta que venza el token.
"""

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import rol_de


def agregar_claims(token, usuario):
    """Escribe en el token los claims propios del usuario y lo devuelve."""
    # SimpleJWT 5.5 convierte user_id a str; se conserva el valor original
    # (entero) para que el claim sea {"user_id": 1} y no {"user_id": "1"}.
    token[api_settings.USER_ID_CLAIM] = getattr(usuario, api_settings.USER_ID_FIELD)
    token["email"] = usuario.email
    token["role"] = rol_de(usuario)
    return token


class LoginTokenSerializer(TokenObtainPairSerializer):
    """Emite el par de tokens del login con los claims propios."""

    @classmethod
    def get_token(cls, user):
        return agregar_claims(super().get_token(user), user)


class RefreshTokenSerializer(TokenRefreshSerializer):
    """Renueva el access con el email y el rol vigentes del usuario.

    Sin esto, el access nuevo heredaria los claims del login y un cambio de
    rol no se veria hasta que el usuario iniciara sesion de nuevo. Ademas,
    un usuario borrado o inactivo recibe 401 en lugar de un 500.
    """

    usuario = None  # el usuario del refresh, disponible tras is_valid()

    def validate(self, attrs):
        usuario = self.usuario = self._usuario_del_refresh(attrs["refresh"])
        datos = super().validate(attrs)

        datos["access"] = str(agregar_claims(AccessToken(datos["access"]), usuario))
        if "refresh" in datos:  # ROTATE_REFRESH_TOKENS
            datos["refresh"] = str(
                agregar_claims(RefreshToken(datos["refresh"]), usuario)
            )
        return datos

    def _usuario_del_refresh(self, refresh: str):
        token = self.token_class(refresh)  # TokenError si es invalido o vencido
        usuario = (
            get_user_model()
            .objects.filter(
                **{
                    api_settings.USER_ID_FIELD: token.payload.get(
                        api_settings.USER_ID_CLAIM
                    )
                }
            )
            .first()
        )
        if usuario is None or not api_settings.USER_AUTHENTICATION_RULE(usuario):
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
        return usuario
