from django.urls import re_path

from .views import ServicioDetailView, ServicioListCreateView

app_name = "catalogo"

urlpatterns = [
    re_path(
        r"^services/?$",
        ServicioListCreateView.as_view(),
        name="service-list",
    ),
    re_path(
        r"^services/(?P<pk>\d+)/?$",
        ServicioDetailView.as_view(),
        name="service-detail",
    ),
]
