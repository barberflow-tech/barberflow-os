from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero, PortfolioBarbero

URL = "/api/v1/barbers/me/portfolio"


@pytest.fixture(autouse=True)
def storage_env(monkeypatch):
    """Configura Storage de prueba para no depender del entorno local o del CI."""
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "clave-de-prueba")
    monkeypatch.setenv("SUPABASE_STORAGE_URL", "http://storage.test")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "barber-portfolios")


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia de prueba", is_active=True)


@pytest.fixture
def usuario_barbero(make_user):
    return make_user("barbero")


@pytest.fixture
def barbero(barberia, usuario_barbero):
    return Barbero.objects.create(
        barberia=barberia, name="Barbero de prueba", user=usuario_barbero
    )


def cliente_api(usuario):
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


@pytest.fixture
def api_autenticada(usuario_barbero, barbero):
    return cliente_api(usuario_barbero)


@pytest.fixture
def imagen_4mb():
    """
    Genera una imagen PNG válida de exactamente 4 MiB.

    Se agrega contenido al final del PNG para alcanzar el tamaño requerido.
    Pillow puede abrir la imagen e ignorar esos bytes adicionales.
    """
    buffer = BytesIO()
    Image.new("RGB", (1200, 1200), color=(40, 120, 180)).save(
        buffer,
        format="PNG",
    )

    contenido = buffer.getvalue()
    tamano_objetivo = 4 * 1024 * 1024

    if len(contenido) >= tamano_objetivo:
        return contenido

    return contenido + (b"\0" * (tamano_objetivo - len(contenido)))


def crear_respuesta_storage():
    respuesta = MagicMock()
    respuesta.__enter__.return_value.status = 200
    respuesta.__enter__.return_value.read.return_value = b""
    return respuesta


@pytest.mark.django_db
def test_barbero_subir_imagen_4mb_y_guardar_portafolio(
    api_autenticada,
    barbero,
    imagen_4mb,
):
    # Dado un barbero autenticado y una imagen válida de 4 MiB
    imagen = SimpleUploadedFile(
        "trabajo.png",
        imagen_4mb,
        content_type="image/png",
    )

    # Cuando carga la imagen y Supabase Storage acepta el archivo
    with patch(
        "urllib.request.urlopen",
        return_value=crear_respuesta_storage(),
    ) as storage_mock:
        response = api_autenticada.post(
            URL,
            {"image": imagen},
            format="multipart",
        )

    # Entonces se crea el registro y se devuelve su URL pública
    assert response.status_code == 201
    assert response.data["image_url"]

    from apps.barberos.models import PortfolioBarbero

    portfolio = PortfolioBarbero.objects.get(pk=response.data["id"])

    assert portfolio.barbero == barbero
    assert portfolio.original_size == 4 * 1024 * 1024
    assert portfolio.optimized_size < 500 * 1024
    assert portfolio.image_url == response.data["image_url"]
    assert portfolio.storage_path

    # El backend realizó una solicitud de carga a Supabase
    storage_mock.assert_called_once()


@pytest.mark.django_db
def test_visitante_no_autenticado_no_puede_subir_imagen():
    # Dado un visitante sin autenticación
    api = APIClient()

    # Cuando intenta subir una imagen
    response = api.post(
        URL,
        {
            "image": SimpleUploadedFile(
                "trabajo.png",
                b"contenido",
                content_type="image/png",
            )
        },
        format="multipart",
    )

    # Entonces la API rechaza la solicitud
    assert response.status_code == 401


def subir_png(api):
    imagen = SimpleUploadedFile("t.png", b"x", content_type="image/png")
    with patch("urllib.request.urlopen") as storage_mock:
        response = api.post(URL, {"image": imagen}, format="multipart")
    return response, storage_mock


@pytest.mark.django_db
def test_cliente_no_puede_subir_al_portafolio(make_user):
    # Dado un usuario con rol cliente
    # Cuando intenta subir una imagen
    response, storage_mock = subir_png(cliente_api(make_user("cliente")))

    # Entonces recibe 403 y no se contacta a Storage
    assert response.status_code == 403
    storage_mock.assert_not_called()


@pytest.mark.django_db
def test_usuario_barbero_sin_barbero_vinculado_recibe_403(usuario_barbero):
    # Dado un usuario con rol barbero que no tiene ficha de Barbero
    # Cuando intenta subir una imagen
    response, storage_mock = subir_png(cliente_api(usuario_barbero))

    # Entonces recibe 403 y no se contacta a Storage
    assert response.status_code == 403
    storage_mock.assert_not_called()


@pytest.mark.django_db
def test_la_imagen_se_guarda_en_el_portafolio_de_su_propio_barbero(
    make_user, barberia, barbero, api_autenticada, imagen_4mb
):
    # Dado otro barbero distinto del autenticado
    otro_usuario = make_user("barbero", email="otro@barberflow.test")
    otro = Barbero.objects.create(barberia=barberia, name="Otro", user=otro_usuario)

    # Cuando el barbero autenticado sube una imagen
    imagen = SimpleUploadedFile("t.png", imagen_4mb, content_type="image/png")
    with patch("urllib.request.urlopen", return_value=crear_respuesta_storage()):
        response = api_autenticada.post(URL, {"image": imagen}, format="multipart")

    # Entonces queda en su portafolio y no en el del otro
    assert response.status_code == 201
    assert barbero.portfolio_images.count() == 1
    assert otro.portfolio_images.count() == 0


@pytest.mark.django_db
def test_rechaza_imagen_mayor_a_5mb(api_autenticada):
    # Dado un archivo que supera el límite de 5 MiB
    contenido = b"x" * (5 * 1024 * 1024 + 1)
    imagen = SimpleUploadedFile(
        "trabajo.png",
        contenido,
        content_type="image/png",
    )

    # Cuando intenta cargarlo
    response = api_autenticada.post(
        URL,
        {"image": imagen},
        format="multipart",
    )

    # Entonces se rechaza y no se persiste ningún portafolio
    assert response.status_code == 400

    from apps.barberos.models import PortfolioBarbero

    assert PortfolioBarbero.objects.count() == 0


@pytest.mark.django_db
def test_rechaza_archivo_que_no_es_una_imagen(api_autenticada):
    # Dado un archivo con extensión PNG pero contenido inválido
    archivo = SimpleUploadedFile(
        "trabajo.png",
        b"esto no es una imagen",
        content_type="image/png",
    )

    # Cuando intenta cargarlo
    response = api_autenticada.post(
        URL,
        {"image": archivo},
        format="multipart",
    )

    # Entonces se rechaza y no se persiste ningún portafolio
    assert response.status_code == 400

    from apps.barberos.models import PortfolioBarbero

    assert PortfolioBarbero.objects.count() == 0


@pytest.mark.django_db
def test_listar_devuelve_solo_las_fotos_del_barbero_autenticado(
    make_user, barberia, barbero, api_autenticada
):
    # Dado un barbero con una foto y otro barbero con otra
    otro = Barbero.objects.create(
        barberia=barberia, name="Otro", user=make_user("barbero", email="o@b.test")
    )
    for dueno, ruta in ((barbero, "a.webp"), (otro, "b.webp")):
        PortfolioBarbero.objects.create(
            barbero=dueno,
            image_url=f"http://storage.test/{ruta}",
            storage_path=ruta,
            original_filename=ruta,
            original_size=10,
            optimized_size=5,
        )

    # Cuando el primero consulta su portafolio
    response = api_autenticada.get(URL)

    # Entonces solo ve la suya
    assert response.status_code == 200
    assert [f["original_filename"] for f in response.data] == ["a.webp"]


@pytest.mark.django_db
def test_listar_exige_rol_barbero(make_user):
    response = cliente_api(make_user("cliente")).get(URL)

    assert response.status_code == 403
