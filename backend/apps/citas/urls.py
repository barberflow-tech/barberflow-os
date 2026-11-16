from django.urls import re_path

from .views import (
    CancelarCitaView,
    CrearCitaView,
    DisponibilidadView,
    ReprogramarCitaView,
)

app_name = "citas"

urlpatterns = [
    # Acepta /appointments y /appointments/: APPEND_SLASH no puede redirigir
    # un POST sin perder el cuerpo.
    re_path(r"^appointments/?$", CrearCitaView.as_view(), name="crear"),
    # \d{1,18} cabe en un BigAutoField: un ID mayor es 404 en la ruta, no un
    # desbordamiento de entero en la consulta.
    re_path(
        r"^appointments/(?P<cita_id>\d{1,18})/cancel/?$",
        CancelarCitaView.as_view(),
        name="cancelar",
    ),
    re_path(
        r"^appointments/(?P<cita_id>\d{1,18})/reschedule/?$",
        ReprogramarCitaView.as_view(),
        name="reprogramar",
    ),
    re_path(r"^availability/?$", DisponibilidadView.as_view(), name="disponibilidad"),
]
