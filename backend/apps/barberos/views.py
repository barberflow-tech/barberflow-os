from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.barberos.context import barbero_de
from apps.barberos.models import PortfolioBarbero
from apps.usuarios.permissions import HasRole

from .serializers import (
    PortfolioBarberoSerializer,
    PortfolioUploadSerializer,
)
from .services import (
    ImageValidationError,
    StorageConfigurationError,
    StorageUploadError,
    delete_from_storage,
    optimize_image,
    upload_to_storage,
)


class PortfolioBarberoUploadView(APIView):
    """Carga una imagen optimizada al portafolio del barbero autenticado."""

    permission_classes = [IsAuthenticated, HasRole("barbero")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Se resuelve antes de procesar o subir nada: sin barbero no hay carga.
        barbero = barbero_de(request.user)
        if barbero is None:
            return Response(
                {"detail": "Tu cuenta no esta vinculada a un barbero activo."},
                status=status.HTTP_403_FORBIDDEN,
            )

        input_serializer = PortfolioUploadSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        uploaded_file = input_serializer.validated_data["image"]

        try:
            optimized_image = optimize_image(uploaded_file)
        except ImageValidationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            image_url, storage_path = upload_to_storage(optimized_image.content)
        except StorageConfigurationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except StorageUploadError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            with transaction.atomic():
                portfolio = PortfolioBarbero.objects.create(
                    barbero=barbero,
                    image_url=image_url,
                    storage_path=storage_path,
                    original_filename=optimized_image.original_filename,
                    original_size=optimized_image.original_size,
                    optimized_size=optimized_image.optimized_size,
                )
        except Exception:
            # Evita dejar un objeto huérfano en Storage si falla PostgreSQL.
            delete_from_storage(storage_path)
            raise

        output_serializer = PortfolioBarberoSerializer(portfolio)

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )
