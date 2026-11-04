from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .context import obtener_barberia_catalogo
from .models import Servicio
from .serializers import ServicioSerializer


class ServicioListCreateView(APIView):
    """GET público y POST administrativo para /api/v1/services."""

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        barberia = obtener_barberia_catalogo()
        servicios = Servicio.objects.filter(barberia=barberia)
        # El público solo ve los activos; el administrador ve también los
        # inactivos para poder reactivarlos (igual que en el detalle).
        if not request.user.is_staff:
            servicios = servicios.filter(is_active=True)
        servicios = servicios.order_by("name")
        serializer = ServicioSerializer(servicios, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ServicioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        servicio = serializer.save(barberia=obtener_barberia_catalogo())
        return Response(
            ServicioSerializer(servicio).data,
            status=status.HTTP_201_CREATED,
        )


class ServicioDetailView(APIView):
    """GET público y PUT/DELETE administrativos para /api/v1/services/{id}."""

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_object(self, request, pk, *, lock=False):
        barberia = obtener_barberia_catalogo()
        queryset = Servicio.objects.filter(barberia=barberia)
        if not request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        if lock:
            queryset = queryset.select_for_update()
        return get_object_or_404(queryset, pk=pk)

    def get(self, request, pk):
        servicio = self.get_object(request, pk)
        return Response(ServicioSerializer(servicio).data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        servicio = self.get_object(request, pk)
        serializer = ServicioSerializer(servicio, data=request.data)
        serializer.is_valid(raise_exception=True)
        servicio = serializer.save()
        return Response(ServicioSerializer(servicio).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        # El borrado es siempre lógico. Nunca se llama a Model.delete().
        # select_for_update + atomic serializan cambios concurrentes sobre
        # el mismo servicio; las citas históricas conservan su FK y su precio.
        with transaction.atomic():
            servicio = self.get_object(request, pk, lock=True)
            if servicio.is_active:
                servicio.is_active = False
                servicio.save(update_fields=["is_active", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)
