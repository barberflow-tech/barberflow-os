"""Resolución temporal del barbero para el portafolio."""

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero

MOCK_BARBERIA_NAME = "BarberFlow Demo (contexto temporal)"
MOCK_BARBER_NAME = "Barbero Demo (contexto temporal)"


def obtener_barbero_portafolio() -> Barbero:
    """Obtiene el barbero de demostración mientras se integra HU-06.

    IMPORTANTE:
    Este contexto es temporal. Todos los usuarios autenticados comparten
    el mismo barbero de demostración. No representa aislamiento multiusuario
    y debe sustituirse por la relación real de usuario-barbero antes de
    utilizar esta funcionalidad en producción.
    """
    barberia, _ = Barberia.objects.get_or_create(
        name=MOCK_BARBERIA_NAME,
        defaults={"is_active": True},
    )

    barbero, _ = Barbero.objects.get_or_create(
        barberia=barberia,
        name=MOCK_BARBER_NAME,
        defaults={"is_active": True},
    )

    return barbero
