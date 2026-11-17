from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.permissions import SoloAdministrador


class FinanzasView(APIView):
    """GET /api/v1/admin/finanzas: punto de entrada protegido del módulo de finanzas.

    Por ahora solo fija el control de acceso de HU-09: los datos financieros
    (ingresos, reportes, métricas y exportaciones) son solo del administrador.
    Sin token responde 401, y con rol barbero o cliente, 403. Los datos reales
    llegan con el POS y las comisiones (Épica 3), que deben colgar de esta
    ruta o de otras con el mismo permiso.
    """

    permission_classes = [SoloAdministrador]

    def get(self, request):
        return Response({"detail": "Acceso concedido al módulo de finanzas."})
