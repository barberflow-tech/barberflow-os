from rest_framework import serializers

from .models import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    """Entrada y representación pública de un servicio del catálogo."""

    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
    )
    duration_minutes = serializers.IntegerField(min_value=1)

    class Meta:
        model = Servicio
        fields = [
            "id",
            "name",
            "price",
            "duration_minutes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
