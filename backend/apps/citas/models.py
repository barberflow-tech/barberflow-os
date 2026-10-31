from datetime import datetime

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models


class TsTzRange(models.Func):
    """TSTZRANGE(inicio, fin) con limites [) de PostgreSQL."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class CitaQuerySet(models.QuerySet):
    def activas(self):
        """Citas que ocupan su franja en la agenda (todas menos canceladas)."""
        return self.exclude(status=Cita.Estado.CANCELLED)

    def solapadas(self, barbero, inicio: datetime, fin: datetime):
        """Citas activas del barbero que se cruzan con [inicio, fin)."""
        return self.activas().filter(
            barber=barbero, start_at__lt=fin, end_at__gt=inicio
        )


class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        COMPLETED = "COMPLETED", "Completada"
        NO_SHOW = "NO_SHOW", "No asistio"

    barberia = models.ForeignKey(
        "barberias.Barberia", on_delete=models.PROTECT, related_name="citas"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    barber = models.ForeignKey(
        "barberos.Barbero", on_delete=models.PROTECT, related_name="citas"
    )
    service = models.ForeignKey(
        "catalogo.Servicio", on_delete=models.PROTECT, related_name="citas"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=Estado.choices, default=Estado.PENDING
    )
    # Copia del precio del servicio al reservar: cambiar el catalogo no
    # altera el historico (HU-10).
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CitaQuerySet.as_manager()

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["barber", "start_at"], name="cita_barbero_inicio_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="cita_fin_posterior_inicio",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="cita_precio_no_negativo",
            ),
            # Respaldo en BD: aunque algun camino se salte el bloqueo del
            # servicio, PostgreSQL rechaza dos citas activas solapadas del
            # mismo barbero.
            ExclusionConstraint(
                name="cita_sin_solapamiento_por_barbero",
                expressions=[
                    (TsTzRange("start_at", "end_at"), RangeOperators.OVERLAPS),
                    ("barber", RangeOperators.EQUAL),
                ],
                condition=~models.Q(status="CANCELLED"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.barber} {self.start_at:%Y-%m-%d %H:%M} ({self.status})"
