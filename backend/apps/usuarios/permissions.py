from functools import cache

from django.conf import settings
from rest_framework.permissions import BasePermission

from .models import Rol, rol_de


class OrigenPermitido(BasePermission):
    """Rechaza las peticiones de navegador cuyo Origin no este autorizado.

    Defensa CSRF para endpoints que dependen de una cookie (refresh): con
    SameSite=None el navegador adjunta la cookie aunque la peticion la dispare
    otro sitio. Los navegadores siempre envian Origin en un POST entre sitios,
    y se compara con CORS_ALLOWED_ORIGINS, la misma lista que ya autoriza al
    frontend. Los clientes que no son navegadores (sin Origin) pasan: no hay
    una cookie ajena que puedan abusar.
    """

    message = "Origen no permitido."

    def has_permission(self, request, view) -> bool:
        origen = request.headers.get("Origin")
        return origen is None or origen in settings.CORS_ALLOWED_ORIGINS


class RolRequerido(BasePermission):
    """Base de los permisos creados con HasRole: el usuario debe tener un rol de `roles`.

    No se usa directamente; sirve para reconocer estos permisos
    (issubclass(permiso, RolRequerido)) y para leer `roles`.
    """

    message = "No tienes permiso para realizar esta accion."
    roles: frozenset[str] = frozenset()

    def has_permission(self, request, view) -> bool:
        # El rol se lee de la base (rol_de), no del claim del token: un cambio
        # de rol surte efecto de inmediato, sin esperar a que el token venza.
        # Un usuario anonimo da None y nunca esta en `roles`. Tampoco cuentan
        # is_staff ni is_superuser: decide solo el rol de la aplicacion.
        return rol_de(request.user) in self.roles


def _normalizar(roles: tuple) -> tuple[str, ...]:
    validos = sorted(Rol.values)
    if not roles:
        raise ValueError(f"HasRole necesita al menos un rol. Validos: {validos}.")
    normalizados = set()
    for rol in roles:
        valor = rol.value if isinstance(rol, Rol) else rol
        if valor not in validos:
            raise ValueError(
                f"Rol desconocido: {rol!r}. Validos (en minusculas): {validos}."
            )
        normalizados.add(valor)
    return tuple(sorted(normalizados))


@cache
def _clase_para(roles: tuple[str, ...]) -> type[RolRequerido]:
    return type(
        f"HasRole_{'_'.join(roles)}", (RolRequerido,), {"roles": frozenset(roles)}
    )


def HasRole(*roles):  # noqa: N802 - se usa como una clase de permiso: HasRole("admin")
    """Permiso DRF por rol: HasRole("admin"), HasRole("admin", "barbero").

    Devuelve una CLASE de permiso (DRF instancia `permission_classes`), asi que
    se escribe igual que cualquier otro permiso y se compone con & y |:

        permission_classes = [HasRole("admin")]
        permission_classes = [HasRole("admin", "barbero")]   # cualquiera de los dos
        permission_classes = [HasRole("admin") | HasRole("barbero")]

    Los roles validos salen del enum Rol, en minusculas; uno desconocido (un
    error de tipeo) lanza ValueError al importar la vista, en lugar de dejar una
    ruta sin proteger. Un usuario sin sesion recibe 401 si la vista tiene
    autenticacion JWT, y 403 si el rol no coincide.
    """
    return _clase_para(_normalizar(roles))
