"""Servicios para optimizar imágenes y almacenarlas en Supabase Storage."""

import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_OPTIMIZED_SIZE = 500 * 1024
MAX_IMAGE_PIXELS = 40_000_000

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
WEBP_QUALITIES = [85, 75, 65, 55, 45, 35]


class ImageValidationError(Exception):
    """La imagen recibida no cumple los requisitos de carga."""


class StorageConfigurationError(Exception):
    """Falta configuración necesaria para conectar con Supabase."""


class StorageUploadError(Exception):
    """Supabase Storage rechazó o no pudo procesar la carga."""


@dataclass
class OptimizedImage:
    content: bytes
    original_size: int
    optimized_size: int
    original_filename: str


def optimize_image(uploaded_file) -> OptimizedImage:
    """Valida y convierte una imagen a WebP optimizado."""

    original_size = uploaded_file.size

    if original_size > MAX_UPLOAD_SIZE:
        raise ImageValidationError(
            "La imagen no puede superar los 5 MiB."
        )

    if original_size == 0:
        raise ImageValidationError("El archivo está vacío.")

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)

        if image.format not in ALLOWED_FORMATS:
            raise ImageValidationError(
                "Formato no permitido. Utiliza JPEG, PNG o WebP."
            )

        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ImageValidationError(
                "La resolución de la imagen es demasiado grande."
            )

        image.load()
        image = ImageOps.exif_transpose(image)

    except ImageValidationError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ImageValidationError(
            "El archivo recibido no contiene una imagen válida."
        ) from exc

    # Conserva transparencia cuando existe; de lo contrario, usa RGB.
    if image.mode in ("RGBA", "LA"):
        optimized = image.convert("RGBA")
    else:
        optimized = image.convert("RGB")

    # Se intenta primero reducir la calidad. Si no es suficiente,
    # se reduce progresivamente la resolución.
    for _ in range(16):
        for quality in WEBP_QUALITIES:
            buffer = BytesIO()

            optimized.save(
                buffer,
                format="WEBP",
                quality=quality,
                method=6,
            )

            content = buffer.getvalue()

            if len(content) < MAX_OPTIMIZED_SIZE:
                return OptimizedImage(
                    content=content,
                    original_size=original_size,
                    optimized_size=len(content),
                    original_filename=uploaded_file.name,
                )

        width, height = optimized.size

        if min(width, height) <= 320:
            break

        new_size = (
            max(320, int(width * 0.85)),
            max(320, int(height * 0.85)),
        )

        optimized.thumbnail(
            new_size,
            Image.Resampling.LANCZOS,
        )

    raise ImageValidationError(
        "No fue posible optimizar la imagen por debajo de 500 KiB."
    )


def _storage_configuration():
    """Obtiene la configuración de Storage sin exponer secretos."""

    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    bucket = os.getenv(
        "SUPABASE_STORAGE_BUCKET",
        "barber-portfolios",
    )

    storage_url = os.getenv("SUPABASE_STORAGE_URL")

    if not storage_url:
        storage_url = os.getenv("SUPABASE_URL", "")

        # Dentro del contenedor, localhost apunta al propio contenedor.
        if "127.0.0.1" in storage_url:
            storage_url = storage_url.replace(
                "127.0.0.1",
                "host.docker.internal",
            )
        elif "localhost" in storage_url:
            storage_url = storage_url.replace(
                "localhost",
                "host.docker.internal",
            )

    if not service_key or not storage_url:
        raise StorageConfigurationError(
            "Supabase Storage no está configurado en el backend."
        )

    return storage_url.rstrip("/"), service_key, bucket


def upload_to_storage(content: bytes) -> tuple[str, str]:
    """Sube un WebP a Supabase y devuelve su URL pública y ruta."""

    base_url, service_key, bucket = _storage_configuration()

    storage_path = f"{uuid4().hex}.webp"
    encoded_path = urllib.parse.quote(storage_path, safe="/")

    endpoint = (
        f"{base_url}/storage/v1/object/{bucket}/{encoded_path}"
    )

    request = urllib.request.Request(
        endpoint,
        data=content,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "image/webp",
            "x-upsert": "false",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in (200, 201):
                raise StorageUploadError(
                    "Supabase no confirmó la carga de la imagen."
                )

    except urllib.error.HTTPError as exc:
        raise StorageUploadError(
            f"Supabase rechazó la carga (HTTP {exc.code})."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise StorageUploadError(
            "No fue posible conectar con Supabase Storage."
        ) from exc

    public_url = (
        f"{base_url}/storage/v1/object/public/"
        f"{bucket}/{encoded_path}"
    )

    return public_url, storage_path


def delete_from_storage(storage_path: str) -> None:
    """Elimina un objeto de Storage, por ejemplo, ante un fallo de BD."""

    base_url, service_key, bucket = _storage_configuration()

    encoded_path = urllib.parse.quote(storage_path, safe="/")
    endpoint = (
        f"{base_url}/storage/v1/object/{bucket}/{encoded_path}"
    )

    request = urllib.request.Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
        },
        method="DELETE",
    )

    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        # No ocultamos el error original que provocó la limpieza.
        pass