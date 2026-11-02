from django.db import models


class Barbero(models.Model):
    """Barbero agendable (modelo minimo de HU-02; HU-07 lo amplia).

    Su fila es el recurso que se bloquea con SELECT ... FOR UPDATE para
    serializar las reservas concurrentes de su agenda.
    """

    barberia = models.ForeignKey(
        "barberias.Barberia", on_delete=models.PROTECT, related_name="barberos"
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
