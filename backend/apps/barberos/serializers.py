from rest_framework import serializers

from apps.barberos.models import PortfolioBarbero
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
