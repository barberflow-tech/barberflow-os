from django.urls import re_path

from .views import LoginView, ProtectedTestView, RefreshView, RegistroView

app_name = "usuarios"

urlpatterns = [
    # Aceptan la ruta con y sin barra final: APPEND_SLASH no puede redirigir
    # un POST sin perder el cuerpo (mismo criterio que citas).
    re_path(r"^auth/register/?$", RegistroView.as_view(), name="register"),
    re_path(r"^auth/login/?$", LoginView.as_view(), name="login"),
    re_path(r"^auth/refresh/?$", RefreshView.as_view(), name="refresh"),
    re_path(
        r"^auth/protected-test/?$", ProtectedTestView.as_view(), name="protected-test"
    ),
]
