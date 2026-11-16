import logging

from django.db import DatabaseError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.barberias.models import barberia_de
from apps.barberos.models import Barbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.usuarios.models import Rol, rol_de
from apps.usuarios.permissions import HasRole

from . import services
from .models import BloqueoAgenda
from .serializers import (
    BloqueoAgendaSerializer,
    CitaSerializer,
    CrearCitaSerializer,
    DisponibilidadQuerySerializer,
    DisponibilidadResponseSerializer,
)

logger = logging.getLogger(__name__)


def barberia_para_reservar(usuario):
    """Barbería en la que el usuario puede ver disponibilidad y reservar.

    El personal usa la de su membresía. Un cliente (o un visitante sin
    cuenta) no tiene membresía, así que reserva en la barbería del catálogo,
    la misma que ve en GET /services: contexto temporal hasta que exista la
    selección de barbería. Cualquier otro usuario sin membresía recibe None.
    """
    if not usuario.is_authenticated:
        return obtener_barberia_catalogo()
    barberia = barberia_de(usuario)
    if barberia is None and rol_de(usuario) == Rol.CLIENTE:
        return obtener_barberia_catalogo()
    return barberia


class ReservaVisitanteThrottle(AnonRateThrottle):
    """Limita las reservas sin cuenta por IP (las autenticadas no se limitan)."""

    scope = "reserva_visitante"


class ReservaEnConflicto(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La franja seleccionada ya no esta disponible."
    default_code = "franja_no_disponible"


class ErrorAlGuardarCita(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "No se pudo registrar la cita. Intenta de nuevo."
    default_code = "error_al_guardar_cita"


class CrearCitaView(APIView):
    """POST /api/v1/appointments: crea una cita PENDING.

    Es publica: con sesion la cita queda a nombre del usuario (acotada a su
    barberia, 403 si no tiene); sin sesion exige nombre y celular de contacto
    y se limita por IP. Los errores usan el formato estandar de DRF
    ({"detail": ...} o errores por campo).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ReservaVisitanteThrottle]

    def post(self, request):
        barberia = barberia_para_reservar(request.user)
        if barberia is None:
            raise PermissionDenied("El usuario no pertenece a ninguna barberia.")

        es_visitante = not request.user.is_authenticated
        entrada = CrearCitaSerializer(
            data=request.data, barberia=barberia, requiere_contacto=es_visitante
        )
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            cita = services.crear_cita(
                cliente=None if es_visitante else request.user,
                contacto_nombre=datos.get("contact_name", "") if es_visitante else "",
                contacto_celular=datos.get("contact_phone", "") if es_visitante else "",
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
    """GET /api/v1/availability/: consulta los slots libres de un barbero (publico)."""

    permission_classes = [AllowAny]

    def get(self, request):
        barberia = barberia_para_reservar(request.user)

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


class GestionBloqueosView(APIView):
    permission_classes = [HasRole(Rol.ADMIN)]

    def barberia_administrada(self, request):
        barberia = barberia_de(request.user)
        if barberia is None:
            raise PermissionDenied("El administrador no pertenece a ninguna barbería.")
        return barberia


class BloqueosAgendaView(GestionBloqueosView):
    def get(self, request):
        barberia = self.barberia_administrada(request)
        bloqueos = BloqueoAgenda.objects.filter(barber__barberia=barberia)
        return Response(BloqueoAgendaSerializer(bloqueos, many=True).data)

    def post(self, request):
        barberia = self.barberia_administrada(request)
        entrada = BloqueoAgendaSerializer(data=request.data, barberia=barberia)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            bloqueo = services.crear_bloqueo(
                barberia=barberia,
                barbero_id=datos["barber"].pk,
                inicio=datos["start_at"],
                fin=datos["end_at"],
                motivo=datos["reason"],
            )
        except services.RecursoInactivoError as exc:
            raise ValidationError({"barber": str(exc)}) from exc

        return Response(
            BloqueoAgendaSerializer(bloqueo).data, status=status.HTTP_201_CREATED
        )


class BloqueoAgendaDetalleView(GestionBloqueosView):
    def delete(self, request, pk):
        barberia = self.barberia_administrada(request)
        bloqueo = get_object_or_404(BloqueoAgenda, pk=pk, barber__barberia=barberia)
        bloqueo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
