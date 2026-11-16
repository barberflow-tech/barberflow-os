from django.urls import re_path

from .views import (
    BarberoListView,
    BarberoServiciosAdminView,
    HorarioDiaView,
    HorarioSemanalView,
    MisServiciosView,
    PortafolioPublicoView,
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
    re_path(
        r"^barbers/me/services/?$",
        MisServiciosView.as_view(),
        name="barber-my-services",
    ),
    re_path(r"^barbers/?$", BarberoListView.as_view(), name="barber-list"),
    re_path(
        r"^barbers/(?P<pk>\d+)/services/?$",
        BarberoServiciosAdminView.as_view(),
        name="barber-services",
    ),
    re_path(r"^portfolio/?$", PortafolioPublicoView.as_view(), name="portfolio-public"),
]
