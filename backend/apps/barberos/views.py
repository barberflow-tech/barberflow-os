from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.barberos.context import obtener_barbero_portafolio
from apps.barberos.models import PortfolioBarbero

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

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
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
            image_url, storage_path = upload_to_storage(
                optimized_image.content
            )
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
                    barbero=obtener_barbero_portafolio(),
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