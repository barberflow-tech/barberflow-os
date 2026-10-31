from django.db import models


class Servicio(models.Model):
    """Servicio reservable (modelo minimo de HU-02; HU-10 lo amplia)."""

    barberia = models.ForeignKey(
        "barberias.Barberia", on_delete=models.PROTECT, related_name="servicios"
    )
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="servicio_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="servicio_duracion_positiva",
            ),
        ]

    def __str__(self) -> str:
        return self.name
