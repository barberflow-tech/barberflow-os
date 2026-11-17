import logging
from contextlib import contextmanager

from django.db import DatabaseError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.barberias.models import barberia_de
from apps.barberos.context import barbero_de
from apps.barberos.models import Barbero, PortfolioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.usuarios.permissions import AdminOBarbero, SoloAdministrador, SoloBarbero

from . import services_horarios
from .serializers import (
    AsignarServiciosSerializer,
    BarberoPublicoSerializer,
    ConflictoCitaSerializer,
    FotoPublicaSerializer,
    HorarioDiaDetalleSerializer,
    HorarioDiaEntradaSerializer,
    HorarioSemanalEntradaSerializer,
    HorarioSemanalSerializer,
    PortfolioBarberoSerializer,
    PortfolioUploadSerializer,
    ServicioPortafolioSerializer,
    datos_horario_semanal,
)
from .services import (
    ImageValidationError,
    StorageConfigurationError,
    StorageUploadError,
    delete_from_storage,
    optimize_image,
    upload_to_storage,
)

logger = logging.getLogger(__name__)


class PortfolioBarberoUploadView(APIView):
    """Carga una imagen optimizada al portafolio del barbero autenticado."""

    permission_classes = [IsAuthenticated, SoloBarbero]
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


class HorarioConCitasFuturas(APIException):
    """409: el cambio dejaría citas futuras fuera del horario del barbero.

    El cuerpo lleva las citas afectadas. Se asigna `detail` ya armado para que
    DRF no convierta los ID y fechas de `conflicts` en texto.
    """

    status_code = status.HTTP_409_CONFLICT
    default_code = "horario_con_citas_futuras"
    mensaje = "El cambio afecta citas futuras. Reprográmalas o cancélalas primero."

    def __init__(self, conflictos):
        super().__init__(self.mensaje)
        self.detail = {
            "detail": self.mensaje,
            "code": self.default_code,
            "conflicts": ConflictoCitaSerializer(conflictos, many=True).data,
        }


class ErrorAlGuardarHorario(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "No se pudo guardar el horario. Intenta de nuevo."
    default_code = "error_al_guardar_horario"


@contextmanager
def errores_de_horario_a_http():
    """Traduce las excepciones de `services_horarios` a excepciones de DRF."""
    try:
        yield
    except (
        services_horarios.BarberoNoEncontradoError,
        services_horarios.HorarioNoEncontradoError,
    ) as exc:
        raise NotFound(str(exc)) from exc
    except services_horarios.HorarioAjenoError as exc:
        raise PermissionDenied(str(exc)) from exc
    except services_horarios.BarberoInactivoError as exc:
        raise ValidationError({"detail": str(exc)}) from exc
    except services_horarios.HorarioInvalidoError as exc:
        raise ValidationError(exc.errores) from exc
    except services_horarios.SemanaInvalidaError as exc:
        raise ValidationError({"days": exc.errores}) from exc
    except services_horarios.CitasAfectadasError as exc:
        raise HorarioConCitasFuturas(exc.conflictos) from exc
    except DatabaseError as exc:
        # El servicio ya hizo ROLLBACK; se responde JSON en vez de un 500 HTML.
        logger.exception("Fallo al guardar el horario del barbero")
        raise ErrorAlGuardarHorario() from exc


class HorarioBarberoBaseView(APIView):
    """Base de las vistas de horarios: por defecto, solo el administrador.

    El barbero puede únicamente VER su propio horario (GET de la semana);
    ver `HorarioSemanalView.get_permissions`.
    """

    permission_classes = [IsAuthenticated, SoloAdministrador]

    @staticmethod
    def barberia_del_admin(usuario):
        barberia = barberia_de(usuario)
        if barberia is None:
            raise PermissionDenied("El usuario no pertenece a ninguna barberia.")
        return barberia


class HorarioSemanalView(HorarioBarberoBaseView):
    """GET/PUT /api/v1/barbers/{id}/schedule: la semana completa del barbero.

    PUT reemplaza la semana en una transacción (los días omitidos quedan sin
    trabajo) y es idempotente. 401 sin sesión, 403 si no es admin, 404 si el
    barbero no existe o es de otra barbería, 400 si algún día no es válido y
    409 si el cambio deja citas futuras fuera del horario.

    GET también lo puede hacer un barbero, pero solo con su propio ID (403 con
    el de otro); PUT sigue siendo solo del administrador.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), AdminOBarbero()]
        return super().get_permissions()

    def get(self, request, barbero_id: int):
        with errores_de_horario_a_http():
            services_horarios.validar_horario_propio(
                usuario=request.user, barbero_id=int(barbero_id)
            )
        barberia = self.barberia_del_admin(request.user)
        with errores_de_horario_a_http():
            barbero, dias = services_horarios.obtener_horario_semanal(
                barbero_id=barbero_id, barberia=barberia
            )
        return Response(
            HorarioSemanalSerializer(datos_horario_semanal(barbero, dias)).data
        )

    def put(self, request, barbero_id: int):
        barberia = self.barberia_del_admin(request.user)
        entrada = HorarioSemanalEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        with errores_de_horario_a_http():
            barbero, dias = services_horarios.reemplazar_horario_semanal(
                barbero_id=barbero_id,
                barberia=barberia,
                dias=entrada.validated_data["days"],
            )
        return Response(
            HorarioSemanalSerializer(datos_horario_semanal(barbero, dias)).data,
            status=status.HTTP_200_OK,
        )


class HorarioDiaView(HorarioBarberoBaseView):
    """PUT/DELETE /api/v1/barbers/{id}/schedule/{weekday}: un día de la semana.

    `weekday` va de 0 (lunes) a 6 (domingo); otro valor no coincide con la
    ruta (404). PUT crea (201) o reemplaza (200) el día sin tocar los demás.
    DELETE lo quita (204).
    """

    def put(self, request, barbero_id: int, weekday: str):
        barberia = self.barberia_del_admin(request.user)
        entrada = HorarioDiaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        with errores_de_horario_a_http():
            horario, creado = services_horarios.definir_horario_dia(
                barbero_id=barbero_id,
                barberia=barberia,
                weekday=int(weekday),
                datos=entrada.validated_data,
            )
        return Response(
            HorarioDiaDetalleSerializer(horario).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

    def delete(self, request, barbero_id: int, weekday: str):
        barberia = self.barberia_del_admin(request.user)
        with errores_de_horario_a_http():
            services_horarios.eliminar_horario_dia(
                barbero_id=barbero_id, barberia=barberia, weekday=int(weekday)
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisServiciosView(APIView):
    """Servicios activos que el admin asignó al barbero autenticado."""

    permission_classes = [IsAuthenticated, SoloBarbero]

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
        .prefetch_related("servicios", "horarios")
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

    permission_classes = [IsAuthenticated, SoloAdministrador]

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
