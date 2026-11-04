from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
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


class HorarioBarbero(models.Model):
    """Horario laboral y descanso de un barbero para un día de la semana."""

    class DiaSemana(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    barbero = models.ForeignKey(
        Barbero,
        on_delete=models.CASCADE,
        related_name="horarios",
    )
    weekday = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    open_time = models.TimeField()
    close_time = models.TimeField()
    break_start = models.TimeField(null=True, blank=True)
    break_duration_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "open_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["barbero", "weekday"],
                name="horario_unico_por_barbero_dia",
            ),
            models.CheckConstraint(
                condition=models.Q(open_time__lt=models.F("close_time")),
                name="horario_apertura_antes_cierre",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        break_start__isnull=True,
                        break_duration_minutes__isnull=True,
                    )
                    | models.Q(
                        break_start__isnull=False,
                        break_duration_minutes__in=[30, 60],
                    )
                ),
                name="horario_descanso_configuracion_valida",
            ),
        ]

    def clean(self):
        super().clean()

        if self.break_start is None:
            if self.break_duration_minutes is not None:
                raise ValidationError(
                    {"break_duration_minutes": "Configura también la hora de inicio."}
                )
            return

        if self.break_duration_minutes not in (30, 60):
            raise ValidationError(
                {"break_duration_minutes": "El descanso debe durar 30 o 60 minutos."}
            )

        jornada = datetime.combine(datetime.min, self.open_time)
        cierre = datetime.combine(datetime.min, self.close_time)
        inicio_descanso = datetime.combine(datetime.min, self.break_start)
        fin_descanso = inicio_descanso + timedelta(minutes=self.break_duration_minutes)

        if inicio_descanso < jornada or fin_descanso > cierre:
            raise ValidationError(
                {"break_start": "El descanso debe estar dentro del horario laboral."}
            )

    @property
    def break_end(self):
        if self.break_start is None or self.break_duration_minutes is None:
            return None

        inicio = datetime.combine(datetime.min, self.break_start)
        return (inicio + timedelta(minutes=self.break_duration_minutes)).time()

    def __str__(self):
        return f"{self.barbero} - {self.get_weekday_display()}"


class PortfolioBarbero(models.Model):
    """Imagen optimizada del portafolio público de un barbero."""

    barbero = models.ForeignKey(
        Barbero,
        on_delete=models.CASCADE,
        related_name="portfolio_images",
    )
    image_url = models.URLField(max_length=500)
    storage_path = models.CharField(max_length=512, unique=True)
    original_filename = models.CharField(max_length=255)
    original_size = models.PositiveBigIntegerField()
    optimized_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "barber_portfolios"

    def __str__(self):
        return f"Portafolio de {self.barbero.name}"
