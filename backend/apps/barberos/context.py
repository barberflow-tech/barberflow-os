"""Resolucion del barbero que corresponde al usuario autenticado."""

from apps.barberos.models import Barbero


def barbero_de(usuario) -> Barbero | None:
    """Barbero activo vinculado a la cuenta, o None si no tiene ninguno."""
    return Barbero.objects.filter(user=usuario, is_active=True).first()
