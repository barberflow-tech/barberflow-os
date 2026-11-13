from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.barberos.context import barbero_de
from apps.barberos.models import Barbero, PortfolioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.usuarios.permissions import HasRole

from .serializers import (
    AsignarServiciosSerializer,
    BarberoPublicoSerializer,
    FotoPublicaSerializer,
    PortfolioBarberoSerializer,
    PortfolioUploadSerializer,
    ServicioPortafolioSerializer,
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

    def get(self, request):
        """Fotos del portafolio del barbero autenticado, de la más reciente a la más antigua."""
        barbero = barbero_de(request.user)
        if barbero is None:
            return Response(
                {"detail": "Tu cuenta no esta vinculada a un barbero activo."},
                status=status.HTTP_403_FORBIDDEN,
            )
        imagenes = PortfolioBarbero.objects.filter(barbero=barbero).select_related(
            "servicio"
        )
        return Response(PortfolioBarberoSerializer(imagenes, many=True).data)

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
        servicio = input_serializer.validated_data["servicio"]

        # El barbero solo publica trabajos de los servicios que le asignó el admin.
        if not barbero.servicios.filter(pk=servicio.pk).exists():
            return Response(
                {"servicio": ["Ese servicio no está asignado a tu perfil."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                    servicio=servicio,
                    nota=input_serializer.validated_data["nota"].strip(),
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


class MisServiciosView(APIView):
    """Servicios activos que el admin asignó al barbero autenticado."""

    permission_classes = [IsAuthenticated, HasRole("barbero")]

    def get(self, request):
        barbero = barbero_de(request.user)
        if barbero is None:
            return Response(
                {"detail": "Tu cuenta no esta vinculada a un barbero activo."},
                status=status.HTTP_403_FORBIDDEN,
            )
        servicios = barbero.servicios.filter(is_active=True).order_by("name")
        return Response(ServicioPortafolioSerializer(servicios, many=True).data)


def _barberos_visibles():
    return (
        Barbero.objects.filter(barberia=obtener_barberia_catalogo(), is_active=True)
        .prefetch_related("servicios")
        .order_by("name")
    )


class BarberoListView(APIView):
    """Barberos de la barbería; con ?service=<id> solo los que hacen ese servicio."""

    permission_classes = [AllowAny]

    def get(self, request):
        barberos = _barberos_visibles()
        servicio = request.query_params.get("service")
        if servicio is not None:
            if not servicio.isdigit():
                return Response(
                    {"service": ["Debe ser un número."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            barberos = barberos.filter(
                servicios__pk=int(servicio), servicios__is_active=True
            )
        return Response(BarberoPublicoSerializer(barberos.distinct(), many=True).data)


class BarberoServiciosAdminView(APIView):
    """El administrador define qué servicios realiza cada barbero."""

    permission_classes = [IsAdminUser]

    def put(self, request, pk):
        barbero = get_object_or_404(_barberos_visibles(), pk=pk)
        serializer = AsignarServiciosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = set(serializer.validated_data["servicios"])
        servicios = Servicio.objects.filter(barberia=barbero.barberia, pk__in=ids)
        if servicios.count() != len(ids):
            return Response(
                {"servicios": ["Hay servicios que no existen en esta barbería."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        barbero.servicios.set(servicios)
        return Response(BarberoPublicoSerializer(barbero).data)


class PortafolioPublicoView(APIView):
    """Fotos que ve el cliente, filtrables por ?barber= y ?service=.

    Solo se muestran trabajos de servicios activos que el barbero siga
    realizando: si el admin desactiva el servicio o se lo quita, la foto se
    oculta (no se borra).
    """

    permission_classes = [AllowAny]
    LIMITE = 24

    def get(self, request):
        fotos = PortfolioBarbero.objects.filter(
            barbero__barberia=obtener_barberia_catalogo(),
            barbero__is_active=True,
            servicio__is_active=True,
            servicio__barberos=F("barbero"),
        ).select_related("barbero", "servicio")

        for parametro, campo in (("barber", "barbero_id"), ("service", "servicio_id")):
            valor = request.query_params.get(parametro)
            if valor is None:
                continue
            if not valor.isdigit():
                return Response(
                    {parametro: ["Debe ser un número."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            fotos = fotos.filter(**{campo: int(valor)})

        fotos = fotos.order_by("-created_at")[: self.LIMITE]
        return Response(FotoPublicaSerializer(fotos, many=True).data)
