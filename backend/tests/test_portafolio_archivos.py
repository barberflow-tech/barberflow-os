"""SCRUM-36 / HU-07: archivos del portafolio en Supabase Storage.

Complementa test_api_portfolio.py con los casos de archivo: formatos validos,
el limite exacto de 5 MiB, archivos disfrazados, fallas de Storage sin dejar
registros ni archivos huerfanos, y subidas simultaneas. Storage siempre va
mockeado (urllib.request.urlopen) para no gastar la cuota de Supabase.
"""

import threading
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection
from PIL import Image
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero, PortfolioBarbero

URL = "/api/v1/barbers/me/portfolio"
LIMITE = 5 * 1024 * 1024
URLOPEN = "urllib.request.urlopen"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def storage_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "clave-de-prueba")
    monkeypatch.setenv("SUPABASE_STORAGE_URL", "http://storage.test")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "barber-portfolios")


@pytest.fixture
def barbero(make_user):
    barberia = Barberia.objects.create(name="Barberia Centro", is_active=True)
    return Barbero.objects.create(
        barberia=barberia, name="Juan", user=make_user("barbero")
    )


@pytest.fixture
def api(barbero):
    api = APIClient()
    api.force_authenticate(user=barbero.user)
    return api


def _respuesta_ok():
    respuesta = MagicMock()
    respuesta.__enter__.return_value.status = 200
    return respuesta


def _imagen(formato="PNG", tamano=(200, 200), relleno_hasta=None):
    buffer = BytesIO()
    Image.new("RGB", tamano, color=(180, 40, 40)).save(buffer, format=formato)
    contenido = buffer.getvalue()
    if relleno_hasta:
        contenido += b"\0" * (relleno_hasta - len(contenido))
    return contenido


def _archivo(contenido, nombre="foto.png", tipo="image/png"):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def _subir(api, archivo):
    return api.post(URL, {"image": archivo}, format="multipart")


# --- FILE-01: formatos validos ------------------------------------------


@pytest.mark.parametrize(
    "formato,nombre,tipo",
    [
        ("JPEG", "corte.jpg", "image/jpeg"),
        ("PNG", "corte.png", "image/png"),
        ("WEBP", "corte.webp", "image/webp"),
    ],
)
def test_file01_sube_jpeg_png_y_webp_como_webp_al_bucket(api, formato, nombre, tipo):
    # Dado un barbero con una imagen valida en cada formato permitido
    with patch(URLOPEN, return_value=_respuesta_ok()) as storage:
        response = _subir(api, _archivo(_imagen(formato), nombre, tipo))

    # Entonces se guarda el registro
    assert response.status_code == 201
    foto = PortfolioBarbero.objects.get(pk=response.data["id"])
    assert foto.original_filename == nombre
    assert foto.storage_path.endswith(".webp")

    # Y a Storage llega un WebP, al bucket correcto y sin sobrescribir otro
    peticion = storage.call_args.args[0]
    assert peticion.get_method() == "POST"
    assert "/storage/v1/object/barber-portfolios/" in peticion.full_url
    assert peticion.headers["Content-type"] == "image/webp"
    assert peticion.headers["X-upsert"] == "false"
    assert peticion.data[:4] == b"RIFF" and peticion.data[8:12] == b"WEBP"


# --- FILE-02: limite de tamano ------------------------------------------


def test_file02_imagen_de_exactamente_5_mib_se_acepta(api):
    contenido = _imagen("PNG", relleno_hasta=LIMITE)
    assert len(contenido) == LIMITE

    with patch(URLOPEN, return_value=_respuesta_ok()):
        response = _subir(api, _archivo(contenido))

    assert response.status_code == 201


def test_file02b_un_byte_por_encima_de_5_mib_se_rechaza(api):
    contenido = _imagen("PNG", relleno_hasta=LIMITE + 1)

    with patch(URLOPEN) as storage:
        response = _subir(api, _archivo(contenido))

    assert response.status_code == 400
    storage.assert_not_called()
    assert not PortfolioBarbero.objects.exists()


# --- FILE-03: archivos no permitidos o disfrazados -----------------------


def _gif():
    buffer = BytesIO()
    Image.new("RGB", (50, 50)).save(buffer, format="GIF")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "contenido,nombre,tipo",
    [
        (b"MZ\x90\x00" + b"\x00" * 200, "foto.jpg", "image/jpeg"),
        (b"%PDF-1.7\n" + b"0" * 200, "portafolio.pdf", "application/pdf"),
        (b"esto es texto plano, no una imagen", "foto.png", "image/png"),
        (_gif(), "animado.gif", "image/gif"),
        (b"", "vacio.png", "image/png"),
    ],
    ids=["exe-como-jpg", "pdf", "texto-como-png", "gif", "vacio"],
)
def test_file03_archivo_no_permitido_se_rechaza_sin_tocar_storage(
    api, contenido, nombre, tipo
):
    # Dado un archivo que no es JPEG/PNG/WebP aunque diga serlo
    with patch(URLOPEN) as storage:
        response = _subir(api, _archivo(contenido, nombre, tipo))

    # Entonces se rechaza antes de subir nada
    assert response.status_code == 400
    storage.assert_not_called()
    assert not PortfolioBarbero.objects.exists()


# --- FILE-07: fallas de Storage o de BD sin huerfanos --------------------


@pytest.mark.parametrize(
    "falla",
    [
        urllib.error.HTTPError("http://storage.test", 413, "Too large", {}, None),
        urllib.error.URLError("sin conexion"),
        TimeoutError(),
    ],
    ids=["storage-rechaza", "sin-conexion", "timeout"],
)
def test_file07_si_storage_falla_retorna_502_sin_registro(api, falla):
    with patch(URLOPEN, side_effect=falla):
        response = _subir(api, _archivo(_imagen()))

    assert response.status_code == 502
    assert not PortfolioBarbero.objects.exists()


def test_file07b_storage_sin_configurar_retorna_503_sin_registro(api, monkeypatch):
    monkeypatch.delenv("SUPABASE_SECRET_KEY")

    with patch(URLOPEN) as storage:
        response = _subir(api, _archivo(_imagen()))

    assert response.status_code == 503
    storage.assert_not_called()
    assert not PortfolioBarbero.objects.exists()


def test_file07c_si_falla_la_bd_se_borra_el_archivo_subido(api):
    # Dado que Storage acepta el archivo pero la BD falla al guardar el registro
    api.raise_request_exception = False
    with (
        patch(URLOPEN, return_value=_respuesta_ok()) as storage,
        patch.object(
            PortfolioBarbero.objects, "create", side_effect=DatabaseError("caida")
        ),
    ):
        response = _subir(api, _archivo(_imagen()))

    # Entonces la peticion falla y el backend borra el archivo recien subido
    assert response.status_code == 500
    subida, borrado = (c.args[0] for c in storage.call_args_list)
    assert subida.get_method() == "POST"
    assert borrado.get_method() == "DELETE"
    assert borrado.full_url == subida.full_url
    assert not PortfolioBarbero.objects.exists()


# --- Permisos -------------------------------------------------------------


def test_barbero_inactivo_no_puede_subir(api, barbero):
    barbero.is_active = False
    barbero.save()

    with patch(URLOPEN) as storage:
        response = _subir(api, _archivo(_imagen()))

    assert response.status_code == 403
    storage.assert_not_called()


# --- FILE-06: subidas simultaneas ----------------------------------------


@pytest.mark.django_db(transaction=True)
def test_file06_cinco_subidas_simultaneas_crean_cinco_registros_distintos(barbero):
    # Dado un barbero que sube 5 fotos al mismo tiempo
    barrera = threading.Barrier(5)
    codigos = [None] * 5
    contenido = _imagen()

    def subir(indice):
        api = APIClient()
        api.force_authenticate(user=barbero.user)
        try:
            barrera.wait()
            codigos[indice] = _subir(
                api, _archivo(contenido, f"foto{indice}.png")
            ).status_code
        finally:
            connection.close()

    with patch(URLOPEN, return_value=_respuesta_ok()):
        hilos = [threading.Thread(target=subir, args=(i,)) for i in range(5)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(30)

    # Entonces las 5 quedan guardadas, cada una con su propio archivo
    assert codigos == [201] * 5
    fotos = PortfolioBarbero.objects.filter(barbero=barbero)
    assert fotos.count() == 5
    assert len({foto.storage_path for foto in fotos}) == 5


# --- FILE-04 y FILE-05: borrado (sin endpoint todavia) -------------------

SIN_DELETE = (
    "Pendiente: SCRUM-35 no expone DELETE del portafolio. "
    "Activar cuando exista el endpoint de borrado."
)


@pytest.mark.skip(reason=SIN_DELETE)
def test_file04_borrar_foto_elimina_registro_y_archivo(api, barbero):
    foto = PortfolioBarbero.objects.create(
        barbero=barbero,
        image_url="http://storage.test/x.webp",
        storage_path="x.webp",
        original_filename="x.png",
        original_size=10,
        optimized_size=5,
    )

    with patch(URLOPEN, return_value=_respuesta_ok()) as storage:
        response = api.delete(f"{URL}/{foto.pk}")

    assert response.status_code == 204
    assert not PortfolioBarbero.objects.exists()
    assert storage.call_args.args[0].get_method() == "DELETE"


@pytest.mark.skip(reason=SIN_DELETE)
def test_file05_barbero_no_puede_borrar_la_foto_de_otro(api, barbero, make_user):
    otro = Barbero.objects.create(
        barberia=barbero.barberia,
        name="Pedro",
        user=make_user("barbero", email="pedro@barberflow.test"),
    )
    foto = PortfolioBarbero.objects.create(
        barbero=otro,
        image_url="http://storage.test/y.webp",
        storage_path="y.webp",
        original_filename="y.png",
        original_size=10,
        optimized_size=5,
    )

    response = api.delete(f"{URL}/{foto.pk}")

    assert response.status_code in (403, 404)
    assert PortfolioBarbero.objects.filter(pk=foto.pk).exists()
