from django.urls import re_path

from .views import (
    BarberoListView,
    BarberoServiciosAdminView,
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
