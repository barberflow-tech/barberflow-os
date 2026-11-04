from django.urls import re_path

from .views import PortfolioBarberoUploadView

app_name = "barberos"

urlpatterns = [
    re_path(
        r"^barbers/me/portfolio/?$",
        PortfolioBarberoUploadView.as_view(),
        name="barber-portfolio-upload",
    ),
]