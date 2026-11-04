"""Cookie HttpOnly del refresh token (HU-06).

El refresh token viaja unicamente en esta cookie, nunca en el cuerpo de la
respuesta. Nombre, Secure, SameSite y path salen de settings.AUTH_REFRESH_COOKIE,
que se ajusta por entorno. Se leen en cada llamada (no al importar) para que
los cambios de configuracion y las pruebas surtan efecto.
"""

from django.conf import settings
from rest_framework_simplejwt.settings import api_settings


def _opciones() -> dict:
    config = settings.AUTH_REFRESH_COOKIE
    return {
        "httponly": True,
        "secure": config["SECURE"],
        "samesite": config["SAMESITE"],
        "path": config["PATH"],
    }


def nombre_cookie_refresh() -> str:
    return settings.AUTH_REFRESH_COOKIE["NAME"]


def poner_cookie_refresh(respuesta, token_refresh: str) -> None:
    """Deja el refresh token en una cookie HttpOnly que dura lo que el token."""
    respuesta.set_cookie(
        nombre_cookie_refresh(),
        token_refresh,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        **_opciones(),
    )


def borrar_cookie_refresh(respuesta) -> None:
    """Pide al navegador eliminar la cookie.

    Se emite con los mismos atributos que set_cookie (path, SameSite, Secure,
    HttpOnly): si no coinciden, el navegador la trata como otra cookie y no
    borra la original, y un SameSite=None sin Secure se rechaza. Se arma con
    set_cookie y no con delete_cookie, que solo recibe path y SameSite y no
    refleja la configuracion de Secure ni de HttpOnly.
    """
    respuesta.set_cookie(
        nombre_cookie_refresh(),
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        **_opciones(),
    )
