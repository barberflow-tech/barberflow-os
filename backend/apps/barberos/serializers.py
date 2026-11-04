from rest_framework import serializers

from apps.barberos.models import PortfolioBarbero

from .services import MAX_UPLOAD_SIZE


class PortfolioUploadSerializer(serializers.Serializer):
    image = serializers.FileField()

    def validate_image(self, value):
        if value.size > MAX_UPLOAD_SIZE:
            raise serializers.ValidationError("La imagen no puede superar los 5 MiB.")

        if value.size == 0:
            raise serializers.ValidationError("El archivo está vacío.")

        return value


class PortfolioBarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioBarbero
        fields = [
            "id",
            "image_url",
            "original_filename",
            "original_size",
            "optimized_size",
            "created_at",
        ]
        read_only_fields = fields
