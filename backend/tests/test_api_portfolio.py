from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero

URL = "/api/v1/barbers/me/portfolio"
MOCK_BARBERIA_NAME = "BarberFlow Demo (contexto temporal)"
MOCK_BARBER_NAME = "Barbero Demo (contexto temporal)"


@pytest.fixture(autouse=True)
def storage_env(monkeypatch):
    """Configura Storage de prueba para no depender del entorno local o del CI."""
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "clave-de-prueba")
    monkeypatch.setenv("SUPABASE_STORAGE_URL", "http://storage.test")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "barber-portfolios")


@pytest.fixture
def barbero():
    barberia, _ = Barberia.objects.get_or_create(
        name=MOCK_BARBERIA_NAME,
        defaults={"is_active": True},
    )
    barbero, _ = Barbero.objects.get_or_create(
        barberia=barberia,
        name=MOCK_BARBER_NAME,
    )
    return barbero


@pytest.fixture
def api_autenticada(django_user_model, barbero):
    usuario = django_user_model.objects.create_user(
        username="barbero_portfolio",
        password="test-password",
    )
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


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
