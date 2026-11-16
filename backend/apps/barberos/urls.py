from django.urls import re_path

from .views import (
    HorarioDiaView,
    HorarioSemanalView,
    PortfolioBarberoUploadView,
)

app_name = "barberos"

urlpatterns = [
    re_path(
        r"^barbers/me/portfolio/?$",
        PortfolioBarberoUploadView.as_view(),
        name="barber-portfolio-upload",
    ),
    # \d{1,18} cabe en un BigAutoField; el dia es 0 (lunes) a 6 (domingo).
    re_path(
        r"^barbers/(?P<barbero_id>\d{1,18})/schedule/?$",
        HorarioSemanalView.as_view(),
        name="horario-semanal",
    ),
    re_path(
        r"^barbers/(?P<barbero_id>\d{1,18})/schedule/(?P<weekday>[0-6])/?$",
        HorarioDiaView.as_view(),
        name="horario-dia",
    ),
]
