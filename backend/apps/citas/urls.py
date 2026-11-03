from django.urls import re_path

from .views import CrearCitaView, DisponibilidadView

app_name = "citas"

urlpatterns = [
    # Acepta /appointments y /appointments/: APPEND_SLASH no puede redirigir
    # un POST sin perder el cuerpo.
    re_path(r"^appointments/?$", CrearCitaView.as_view(), name="crear"),
    re_path(r"^availability/?$", DisponibilidadView.as_view(), name="disponibilidad"),
]
