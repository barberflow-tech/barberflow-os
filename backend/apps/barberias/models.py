from django.conf import settings
from django.db import models


class Barberia(models.Model):
    """Tenant del SaaS: duena de sus barberos, servicios y citas.

    Modelo minimo de HU-02 para aislar las reservas entre negocios.
    """

    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membresia(models.Model):
    """Barberia a la que pertenece un usuario (HU-02; la Epica 2 agrega el rol)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membresia"
    )
    barberia = models.ForeignKey(
        Barberia, on_delete=models.PROTECT, related_name="membresias"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} @ {self.barberia}"


def barberia_de(user) -> Barberia | None:
    """Barberia activa del usuario, o None si no pertenece a ninguna."""
    membresia = (
        Membresia.objects.select_related("barberia")
        .filter(user_id=user.pk, barberia__is_active=True)
        .first()
    )
    return membresia.barberia if membresia else None
