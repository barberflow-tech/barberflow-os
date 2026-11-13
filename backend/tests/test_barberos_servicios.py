"""Servicios por barbero (los asigna el admin) y portafolio público."""

import pytest
from rest_framework.test import APIClient

from apps.barberos.models import Barbero, PortfolioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio


@pytest.fixture
def barberia(db):
    return obtener_barberia_catalogo()


@pytest.fixture
def fade(barberia):
    return Servicio.objects.create(
        barberia=barberia, name="Fade", price="35000.00", duration_minutes=45
    )


@pytest.fixture
def barba(barberia):
    return Servicio.objects.create(
        barberia=barberia, name="Barba", price="25000.00", duration_minutes=30
    )


@pytest.fixture
def thiago(barberia, fade):
    barbero = Barbero.objects.create(barberia=barberia, name="Thiago")
    barbero.servicios.add(fade)
    return barbero


@pytest.fixture
def andres(barberia, fade, barba):
    barbero = Barbero.objects.create(barberia=barberia, name="Andrés")
    barbero.servicios.add(fade, barba)
    return barbero


def foto(barbero, servicio, n=1):
    return PortfolioBarbero.objects.create(
        barbero=barbero,
        servicio=servicio,
        image_url=f"http://x.test/{barbero.pk}-{servicio.pk}-{n}.webp",
        storage_path=f"{barbero.pk}-{servicio.pk}-{n}.webp",
        original_filename="a.png",
        original_size=10,
        optimized_size=5,
    )


def admin_api(make_user):
    api = APIClient()
    api.force_authenticate(user=make_user("admin"))
    return api


@pytest.mark.django_db
def test_lista_publica_de_barberos_con_sus_servicios(thiago, andres, fade, barba):
    response = APIClient().get("/api/v1/barbers")

    assert response.status_code == 200
    por_nombre = {b["name"]: b["servicios"] for b in response.data}
    assert por_nombre["Thiago"] == [fade.pk]
    assert sorted(por_nombre["Andrés"]) == sorted([fade.pk, barba.pk])


@pytest.mark.django_db
def test_filtrar_barberos_por_servicio(thiago, andres, barba):
    response = APIClient().get(f"/api/v1/barbers?service={barba.pk}")

    assert [b["name"] for b in response.data] == ["Andrés"]


@pytest.mark.django_db
def test_filtro_de_servicio_invalido_da_400():
    assert APIClient().get("/api/v1/barbers?service=abc").status_code == 400


@pytest.mark.django_db
def test_no_lista_barberos_inactivos(thiago):
    thiago.is_active = False
    thiago.save()

    assert APIClient().get("/api/v1/barbers").data == []


@pytest.mark.django_db
def test_admin_asigna_servicios_a_un_barbero(make_user, thiago, fade, barba):
    response = admin_api(make_user).put(
        f"/api/v1/barbers/{thiago.pk}/services",
        {"servicios": [barba.pk]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["servicios"] == [barba.pk]
    assert list(thiago.servicios.all()) == [barba]


@pytest.mark.django_db
def test_admin_puede_quitar_todos_los_servicios(make_user, thiago):
    response = admin_api(make_user).put(
        f"/api/v1/barbers/{thiago.pk}/services", {"servicios": []}, format="json"
    )

    assert response.status_code == 200
    assert thiago.servicios.count() == 0


@pytest.mark.django_db
def test_asignar_servicios_inexistentes_da_400(make_user, thiago):
    response = admin_api(make_user).put(
        f"/api/v1/barbers/{thiago.pk}/services", {"servicios": [99999]}, format="json"
    )

    assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("rol", ["cliente", "barbero"])
def test_solo_el_admin_asigna_servicios(make_user, thiago, fade, rol):
    api = APIClient()
    api.force_authenticate(user=make_user(rol))

    response = api.put(
        f"/api/v1/barbers/{thiago.pk}/services", {"servicios": [fade.pk]}, format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_visitante_no_asigna_servicios(thiago, fade):
    response = APIClient().put(
        f"/api/v1/barbers/{thiago.pk}/services", {"servicios": [fade.pk]}, format="json"
    )

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_portafolio_publico_filtra_por_barbero_y_servicio(thiago, andres, fade, barba):
    foto(thiago, fade)
    foto(andres, fade)
    foto(andres, barba)

    todas = APIClient().get("/api/v1/portfolio").data
    de_andres = APIClient().get(f"/api/v1/portfolio?barber={andres.pk}").data
    barba_andres = (
        APIClient().get(f"/api/v1/portfolio?barber={andres.pk}&service={barba.pk}").data
    )

    assert len(todas) == 3
    assert len(de_andres) == 2
    assert len(barba_andres) == 1
    assert barba_andres[0]["servicio"]["name"] == "Barba"
    assert barba_andres[0]["barbero"]["name"] == "Andrés"


@pytest.mark.django_db
def test_portafolio_oculta_servicios_desactivados_o_quitados(thiago, fade):
    foto(thiago, fade)

    fade.is_active = False
    fade.save()
    assert APIClient().get("/api/v1/portfolio").data == []

    fade.is_active = True
    fade.save()
    assert len(APIClient().get("/api/v1/portfolio").data) == 1

    thiago.servicios.remove(fade)
    assert APIClient().get("/api/v1/portfolio").data == []


@pytest.mark.django_db
def test_portafolio_oculta_barberos_inactivos(thiago, fade):
    foto(thiago, fade)
    thiago.is_active = False
    thiago.save()

    assert APIClient().get("/api/v1/portfolio").data == []


@pytest.mark.django_db
def test_portafolio_filtro_invalido_da_400():
    assert APIClient().get("/api/v1/portfolio?barber=x").status_code == 400
