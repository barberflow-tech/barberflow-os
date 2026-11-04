"""Contexto temporal del catálogo mientras HU-06 finaliza.

Este módulo concentra el único punto que debe cambiar al conectar el catálogo
con el usuario autenticado y su membresía de barbería.
"""

from apps.barberias.models import Barberia

MOCK_BARBERIA_NAME = "BarberFlow Demo (contexto temporal)"


def obtener_barberia_catalogo() -> Barberia:
    """Devuelve la barbería de demostración usada temporalmente por el catálogo.

    Cuando HU-06 esté lista, sustituir el cuerpo por la resolución de la
    barbería asociada al usuario autenticado (por ejemplo, barberia_de(user)).
    """
    barberia, _ = Barberia.objects.get_or_create(
        name=MOCK_BARBERIA_NAME,
        defaults={"is_active": True},
    )
    return barberia
