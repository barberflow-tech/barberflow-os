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

    def solapadas(
        self, barbero, inicio: datetime, fin: datetime, excluyendo: int | None = None
    ):
        """Citas activas del barbero que se cruzan con [inicio, fin).

        `excluyendo` (ID de cita) deja fuera a la cita que se está moviendo:
        sin eso, reprogramarla 15 min chocaría con su propia franja anterior.
        """
        solapadas = self.activas().filter(
            barber=barbero, start_at__lt=fin, end_at__gt=inicio
        )
        if excluyendo is not None:
            solapadas = solapadas.exclude(pk=excluyendo)
        return solapadas


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
    # Nulo cuando la cita la agenda un visitante sin cuenta: entonces el
    # contacto va en contact_name / contact_phone.
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="citas",
        null=True,
        blank=True,
    )
    contact_name = models.CharField(max_length=80, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
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
    # Cancelacion por el cliente (HU-03). `late_cancellation` congela la
    # decision con la regla vigente ese dia (12 h o menos de antelacion) para
    # que HU-19 (SmartGuard) la cuente sin recalcularla. Las citas canceladas
    # antes de existir estos campos quedan con cancelled_at nulo.
    cancelled_at = models.DateTimeField(null=True, blank=True)
    late_cancellation = models.BooleanField(default=False)
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
            # Toda cita tiene dueño: una cuenta o un contacto de visitante.
            models.CheckConstraint(
                condition=models.Q(client__isnull=False)
                | (~models.Q(contact_name="") & ~models.Q(contact_phone="")),
                name="cita_con_cliente_o_contacto",
            ),
            # La marca de cancelacion tardia solo existe en citas canceladas.
            models.CheckConstraint(
                condition=models.Q(late_cancellation=False)
                | models.Q(status="CANCELLED"),
                name="cita_tardia_solo_si_cancelada",
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
