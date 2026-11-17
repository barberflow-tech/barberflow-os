from django.utils import timezone
from rest_framework import serializers

from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio

from .models import BloqueoAgenda, Cita
from .services import (
    ANTICIPACION_MINIMA,
    ANTICIPACION_MINIMA_HORAS,
    ZONA_HORARIA_BARBERIA,
    resumen_citas_afectadas,
)


class CrearCitaSerializer(serializers.Serializer):
    """Payload de entrada de POST /api/v1/appointments.

    Solo valida forma, tipos y existencia dentro de la barberia del usuario.
    La disponibilidad se decide en services.crear_cita, con el bloqueo del
    barbero adquirido.
    """

    barber = serializers.PrimaryKeyRelatedField(queryset=Barbero.objects.none())
    service = serializers.PrimaryKeyRelatedField(queryset=Servicio.objects.none())
    start_at = serializers.DateTimeField()
    # Contacto del visitante sin cuenta; se exige solo cuando no hay sesion.
    contact_name = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        min_length=3,
        max_length=80,
    )
    contact_phone = serializers.RegexField(
        r"^3\d{9}$",
        required=False,
        allow_blank=True,
        error_messages={"invalid": "Ingresa un celular colombiano de 10 digitos."},
    )

    def __init__(self, *args, barberia, requiere_contacto=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.requiere_contacto = requiere_contacto
        self.fields["barber"].queryset = Barbero.objects.filter(
            barberia=barberia, is_active=True
        )
        self.fields["service"].queryset = Servicio.objects.filter(
            barberia=barberia, is_active=True
        )

    def validate(self, attrs):
        if self.requiere_contacto:
            faltan = {
                campo: "Este campo es obligatorio."
                for campo in ("contact_name", "contact_phone")
                if not attrs.get(campo)
            }
            if faltan:
                raise serializers.ValidationError(faltan)
        return attrs

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


class ServicioDeCitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ["id", "name", "price", "duration_minutes", "description"]
        read_only_fields = fields


class BarberoDeCitaSerializer(serializers.ModelSerializer):
    working_days = serializers.SerializerMethodField()

    class Meta:
        model = Barbero
        fields = ["id", "name", "working_days"]
        read_only_fields = fields

    def get_working_days(self, barbero) -> list[int]:
        """Dias que atiende (0 lunes a 6 domingo): el modal de reprogramar solo ofrece esos."""
        return sorted({h.weekday for h in barbero.horarios.all() if h.is_active})


class CitaPerfilSerializer(serializers.ModelSerializer):
    """Cita tal como la ve el cliente en su perfil: con servicio y barbero.

    Lleva la regla de antelacion ya calculada para que el frontend no la
    duplique: `reschedule_deadline` es el ultimo instante (exclusivo) en que
    aun se puede reprogramar y `min_notice_hours` la antelacion que la define.
    """

    service = ServicioDeCitaSerializer(read_only=True)
    barber = BarberoDeCitaSerializer(read_only=True)
    reschedule_deadline = serializers.SerializerMethodField()
    min_notice_hours = serializers.SerializerMethodField()
    # Solo si la afecta un bloqueo: el motivo del bloqueo es interno y no se expone.
    affected_by_block = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "status",
            "start_at",
            "end_at",
            "price",
            "service",
            "barber",
            "reschedule_deadline",
            "min_notice_hours",
            "affected_by_block",
        ]
        read_only_fields = fields

    def get_reschedule_deadline(self, cita):
        return cita.start_at - ANTICIPACION_MINIMA

    def get_min_notice_hours(self, cita) -> int:
        return ANTICIPACION_MINIMA_HORAS

    def get_affected_by_block(self, cita) -> bool:
        return cita.affected_by_block_id is not None


class CitaHistorialSerializer(serializers.ModelSerializer):
    """Cita que ya no está activa, como la ve el cliente en «Canceladas».

    `outcome` dice por qué: `cancelled` si la canceló el cliente y `expired` si
    la hora pasó sin atenderse (vencida o marcada como no asistida).
    """

    service = ServicioDeCitaSerializer(read_only=True)
    barber = BarberoDeCitaSerializer(read_only=True)
    outcome = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "status",
            "outcome",
            "start_at",
            "end_at",
            "price",
            "service",
            "barber",
            "cancelled_at",
            "late_cancellation",
        ]
        read_only_fields = fields

    def get_outcome(self, cita) -> str:
        return "cancelled" if cita.status == Cita.Estado.CANCELLED else "expired"


class ReprogramarCitaSerializer(serializers.Serializer):
    """Payload de entrada de POST /api/v1/appointments/{id}/reschedule.

    Solo valida forma y tipo. Las reglas (propietario, antelacion, disponibilidad)
    se deciden en services.reprogramar_cita, con los bloqueos adquiridos.
    """

    start_at = serializers.DateTimeField()


class CitaCanceladaSerializer(CitaSerializer):
    """Salida de POST /appointments/{id}/cancel: la cita y cómo se canceló."""

    class Meta(CitaSerializer.Meta):
        fields = [*CitaSerializer.Meta.fields, "cancelled_at", "late_cancellation"]
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


class BloqueoAgendaSerializer(serializers.ModelSerializer):
    barber = serializers.PrimaryKeyRelatedField(queryset=Barbero.objects.none())
    start_at = serializers.DateTimeField(default_timezone=ZONA_HORARIA_BARBERIA)
    end_at = serializers.DateTimeField(default_timezone=ZONA_HORARIA_BARBERIA)
    affected_appointments = serializers.SerializerMethodField()

    class Meta:
        model = BloqueoAgenda
        fields = [
            "id",
            "barber",
            "start_at",
            "end_at",
            "reason",
            "affected_appointments",
        ]
        read_only_fields = ["id"]

    def get_affected_appointments(self, bloqueo) -> dict:
        """Citas afectadas y estado de su aviso (HU-04). Usa el prefetch si lo hay."""
        return resumen_citas_afectadas(bloqueo.citas_afectadas.all())

    def __init__(self, *args, barberia=None, **kwargs):
        super().__init__(*args, **kwargs)
        if barberia is not None:
            self.fields["barber"].queryset = Barbero.objects.filter(
                barberia=barberia, is_active=True
            )

    def validate(self, attrs):
        if attrs["end_at"] <= attrs["start_at"]:
            raise serializers.ValidationError(
                {"end_at": "El fin debe ser posterior al inicio."}
            )
        return attrs
