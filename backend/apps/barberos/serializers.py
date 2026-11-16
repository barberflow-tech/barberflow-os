from rest_framework import serializers

from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.barberos.models import HorarioBarbero, PortfolioBarbero
from apps.catalogo.models import Servicio

from .services import MAX_UPLOAD_SIZE


class PortfolioUploadSerializer(serializers.Serializer):
    image = serializers.FileField()
    # Toda foto demuestra un servicio del catálogo; la vista comprueba además
    # que el barbero lo tenga asignado.
    servicio = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.filter(is_active=True)
    )
    nota = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )

    def validate_image(self, value):
        if value.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("La imagen no puede superar los 5 MiB.")

        if value.size == 0:
            raise serializers.ValidationError("El archivo está vacío.")

        return value


class ServicioPortafolioSerializer(serializers.ModelSerializer):
    """Datos del corte tal como los define el administrador."""

    class Meta:
        model = Servicio
        fields = ["id", "name", "price", "duration_minutes", "description"]
        read_only_fields = fields


class PortfolioBarberoSerializer(serializers.ModelSerializer):
    servicio = ServicioPortafolioSerializer(read_only=True)

    class Meta:
        model = PortfolioBarbero
        fields = [
            "id",
            "servicio",
            "nota",
            "image_url",
            "original_filename",
            "original_size",
            "optimized_size",
            "created_at",
        ]
        read_only_fields = fields


# --------------------------------------------------------------------------- #
# Horarios del barbero (HU-08)                                                #
# --------------------------------------------------------------------------- #

MAXIMO_DIAS_SEMANA = 7
FORMATO_HORA = "%H:%M"


class HoraField(serializers.TimeField):
    """Hora de pared "HH:MM" (sin segundos) en la hora de la barbería."""

    def __init__(self, **kwargs):
        super().__init__(format=FORMATO_HORA, input_formats=[FORMATO_HORA], **kwargs)


class FechaHoraBarberiaField(serializers.DateTimeField):
    """Fecha y hora ISO 8601 con el desfase de la barbería (-05:00)."""

    def to_representation(self, value):
        if value is None:
            return None
        return value.astimezone(ZONA_HORARIA_BARBERIA).isoformat()


class HorarioDiaEntradaSerializer(serializers.Serializer):
    """Turno y descanso de un día. Solo valida forma y tipos.

    Las reglas (cierre > apertura, descanso dentro del turno, citas futuras)
    se deciden en `services_horarios`, con el barbero bloqueado.
    """

    open_time = HoraField()
    close_time = HoraField()
    break_start = HoraField(required=False, allow_null=True)
    break_duration_minutes = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )


class HorarioSemanaDiaEntradaSerializer(HorarioDiaEntradaSerializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)


class HorarioSemanalEntradaSerializer(serializers.Serializer):
    """Payload de PUT /barbers/{id}/schedule: la semana completa."""

    days = HorarioSemanaDiaEntradaSerializer(
        many=True, allow_empty=False, max_length=MAXIMO_DIAS_SEMANA
    )


class HorarioDiaSerializer(serializers.ModelSerializer):
    """Un día laborable tal como se devuelve dentro de la semana."""

    open_time = HoraField(read_only=True)
    close_time = HoraField(read_only=True)
    break_start = HoraField(read_only=True)

    class Meta:
        model = HorarioBarbero
        fields = [
            "weekday",
            "open_time",
            "close_time",
            "break_start",
            "break_duration_minutes",
        ]
        read_only_fields = fields


class HorarioDiaDetalleSerializer(HorarioDiaSerializer):
    """Respuesta de PUT /barbers/{id}/schedule/{weekday}."""

    barber = serializers.IntegerField(source="barbero_id", read_only=True)
    updated_at = FechaHoraBarberiaField(read_only=True)

    class Meta(HorarioDiaSerializer.Meta):
        fields = ["barber", *HorarioDiaSerializer.Meta.fields, "updated_at"]
        read_only_fields = fields


class HorarioSemanalSerializer(serializers.Serializer):
    """Respuesta de GET y PUT /barbers/{id}/schedule."""

    barber = serializers.IntegerField()
    name = serializers.CharField()
    timezone = serializers.CharField()
    days = HorarioDiaSerializer(many=True)
    updated_at = FechaHoraBarberiaField(allow_null=True)


class ConflictoCitaSerializer(serializers.Serializer):
    """Una cita futura que el cambio de horario dejaría fuera de jornada."""

    appointment = serializers.IntegerField(source="cita_id")
    start_at = FechaHoraBarberiaField(source="inicio")
    reason = serializers.CharField(source="motivo")


def datos_horario_semanal(barbero, horarios) -> dict:
    """Arma el dato de `HorarioSemanalSerializer` desde el barbero y sus días."""
    return {
        "barber": barbero.pk,
        "name": barbero.name,
        "timezone": ZONA_HORARIA_BARBERIA.key,
        "days": horarios,
        "updated_at": max((h.updated_at for h in horarios), default=None),
    }


class BarberoPublicoSerializer(serializers.Serializer):
    """Barbero visible al cliente, con los servicios que realiza."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    servicios = serializers.SerializerMethodField()

    def get_servicios(self, barbero):
        return [s.pk for s in barbero.servicios.all() if s.is_active]


class AsignarServiciosSerializer(serializers.Serializer):
    servicios = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=True
    )


class FotoPublicaSerializer(serializers.ModelSerializer):
    """Foto del portafolio tal como la ve un cliente."""

    servicio = ServicioPortafolioSerializer(read_only=True)
    barbero = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioBarbero
        fields = ["id", "image_url", "nota", "created_at", "servicio", "barbero"]
        read_only_fields = fields

    def get_barbero(self, foto):
        return {"id": foto.barbero_id, "name": foto.barbero.name}
