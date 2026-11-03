from django.utils import timezone
from rest_framework import serializers

from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio

from .models import Cita


class CrearCitaSerializer(serializers.Serializer):
    """Payload de entrada de POST /api/v1/appointments.

    Solo valida forma, tipos y existencia dentro de la barberia del usuario.
    La disponibilidad se decide en services.crear_cita, con el bloqueo del
    barbero adquirido.
    """

    barber = serializers.PrimaryKeyRelatedField(queryset=Barbero.objects.none())
    service = serializers.PrimaryKeyRelatedField(queryset=Servicio.objects.none())
    start_at = serializers.DateTimeField()

    def __init__(self, *args, barberia, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["barber"].queryset = Barbero.objects.filter(
            barberia=barberia, is_active=True
        )
        self.fields["service"].queryset = Servicio.objects.filter(
            barberia=barberia, is_active=True
        )

    def validate_start_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("La cita debe ser en el futuro.")
        return value


class CitaSerializer(serializers.ModelSerializer):
    """Representacion de salida de una cita."""

    class Meta:
        model = Cita
        fields = ["id", "status", "barber", "service", "start_at", "end_at", "price"]
        read_only_fields = fields


class DisponibilidadQuerySerializer(serializers.Serializer):
    """Valida los parámetros de consulta de disponibilidad."""

    barber = serializers.IntegerField(min_value=1)
    date = serializers.DateField()
    slot_duration = serializers.ChoiceField(choices=(30, 60))


class SlotDisponibleSerializer(serializers.Serializer):
    """Representación de un intervalo libre."""

    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class DisponibilidadResponseSerializer(serializers.Serializer):
    """Respuesta de GET /api/v1/availability/."""

    barber = serializers.IntegerField()
    date = serializers.DateField()
    slot_duration = serializers.IntegerField()
    available_slots = SlotDisponibleSerializer(many=True)