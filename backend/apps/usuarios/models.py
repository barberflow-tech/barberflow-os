from django.conf import settings
from django.db import models


class Rol(models.TextChoices):
    """Roles de RBAC (HU-06). Siempre en minusculas, tal como los usa el frontend."""

    ADMIN = "admin", "Administrador"
    BARBERO = "barbero", "Barbero"
    CLIENTE = "cliente", "Cliente"


class PerfilUsuario(models.Model):
    """Datos de aplicacion del usuario; por ahora, su rol.

    Vive aparte de Membresia a proposito: el rol es del usuario, no de su
    vinculo con una barberia, y un cliente existe sin barberia.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    role = models.CharField(max_length=16, choices=Rol.choices, default=Rol.CLIENTE)
    full_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Respaldo en BD para caminos que se saltan save() (update masivo).
            models.CheckConstraint(
                condition=models.Q(role__in=Rol.values),
                name="perfil_rol_valido",
            ),
        ]

    def save(self, *args, **kwargs):
        self.role = str(self.role).strip().lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user} ({self.role})"


def rol_de(usuario) -> str | None:
    """Rol del usuario: None si es anonimo; cliente si no tiene perfil.

    Si falta el perfil se asume el rol de menor privilegio, nunca uno superior.
    """
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None
    try:
        return usuario.perfil.role
    except PerfilUsuario.DoesNotExist:
        return Rol.CLIENTE.value
