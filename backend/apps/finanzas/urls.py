from django.urls import re_path

from .views import FinanzasView

app_name = "finanzas"

urlpatterns = [
    # Acepta /admin/finanzas y /admin/finanzas/ (mismo criterio que citas).
    re_path(r"^admin/finanzas/?$", FinanzasView.as_view(), name="finanzas"),
]
