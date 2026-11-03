import logging

from django.db import DatabaseError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.barberias.models import barberia_de
from apps.barberos.models import Barbero

from . import services
from .serializers import (
    CitaSerializer,
    CrearCitaSerializer,
    DisponibilidadQuerySerializer,
    DisponibilidadResponseSerializer,
)

logger = logging.getLogger(__name__)


class ReservaEnConflicto(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La franja seleccionada ya no esta disponible."
    default_code = "franja_no_disponible"


class ErrorAlGuardarCita(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "No se pudo registrar la cita. Intenta de nuevo."
    default_code = "error_al_guardar_cita"


class CrearCitaView(APIView):
    """POST /api/v1/appointments: crea una cita PENDING para el usuario autenticado.

    Autenticacion (JWT) y permiso (IsAuthenticated) vienen de REST_FRAMEWORK
    en settings. La reserva queda acotada a la barberia del usuario (403 si
    no pertenece a ninguna). Los errores usan el formato estandar de DRF ({"detail": ...}
    o errores por campo).
    """

    def post(self, request):
        barberia = barberia_de(request.user)
        if barberia is None:
            raise PermissionDenied("El usuario no pertenece a ninguna barberia.")

        entrada = CrearCitaSerializer(data=request.data, barberia=barberia)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            cita = services.crear_cita(
                cliente=request.user,
                barberia=barberia,
                barbero_id=datos["barber"].pk,
                servicio_id=datos["service"].pk,
                inicio=datos["start_at"],
            )
        except services.FranjaNoDisponibleError as exc:
            raise ReservaEnConflicto(str(exc)) from exc
        except (services.HorarioInvalidoError, services.RecursoInactivoError) as exc:
            # Estado que cambio entre la validacion y el bloqueo.
            raise ValidationError({"detail": str(exc)}) from exc
        except DatabaseError as exc:
            # crear_cita ya hizo ROLLBACK; se responde JSON en vez de un 500 HTML.
            logger.exception("Fallo al guardar la cita")
            raise ErrorAlGuardarCita() from exc

        return Response(CitaSerializer(cita).data, status=status.HTTP_201_CREATED)


class DisponibilidadView(APIView):
    """GET /api/v1/availability/: consulta los slots libres de un barbero."""

    def get(self, request):
        barberia = barberia_de(request.user)

        if barberia is None:
            raise PermissionDenied("El usuario no pertenece a ninguna barbería.")

        entrada = DisponibilidadQuerySerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        barbero = Barbero.objects.filter(
            pk=datos["barber"],
            barberia=barberia,
            is_active=True,
        ).first()

        if barbero is None:
            raise NotFound("El barbero solicitado no existe.")

        try:
            slots = services.obtener_slots_libres(
                barbero=barbero,
                fecha=datos["date"],
                duracion_minutos=datos["slot_duration"],
            )
        except ValueError as exc:
            raise ValidationError({"slot_duration": str(exc)}) from exc

        resultado = DisponibilidadResponseSerializer(
            {
                "barber": barbero.pk,
                "date": datos["date"],
                "slot_duration": datos["slot_duration"],
                "available_slots": slots,
            }
        )

        return Response(resultado.data, status=status.HTTP_200_OK)
