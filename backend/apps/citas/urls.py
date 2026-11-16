from django.urls import re_path

from .views import (
    BloqueoAgendaDetalleView,
    BloqueosAgendaView,
    CrearCitaView,
    DisponibilidadView,
)

app_name = "citas"

urlpatterns = [
    re_path(r"^blocks/?$", BloqueosAgendaView.as_view(), name="bloqueos"),
    re_path(
        r"^blocks/(?P<pk>[0-9]+)/?$",
        BloqueoAgendaDetalleView.as_view(),
        name="bloqueo-detalle",
    ),
    # Acepta /appointments y /appointments/: APPEND_SLASH no puede redirigir
    # un POST sin perder el cuerpo.
    re_path(r"^appointments/?$", CrearCitaView.as_view(), name="crear"),
    re_path(r"^availability/?$", DisponibilidadView.as_view(), name="disponibilidad"),
]
