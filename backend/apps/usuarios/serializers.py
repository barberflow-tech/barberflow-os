from collections.abc import Mapping

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from .models import Rol

User = get_user_model()

# AbstractUser.username admite 150 caracteres y aqui guarda el email.
LONGITUD_MAX_EMAIL = 150
EMAIL_DUPLICADO = "Ya existe una cuenta con este correo."


class CredencialesInvalidas(APIException):
    """401 generico: no revela si fallo el correo o la contrasena.

    No se usa AuthenticationFailed de DRF porque, en una vista sin clases de
    autenticacion, DRF la convierte en 403.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Correo o contrasena incorrectos."
    default_code = "credenciales_invalidas"


class RegistroSerializer(serializers.Serializer):
    """Payload de POST /api/v1/auth/register.

    Solo declara email, password y un nombre opcional. Cualquier otro campo
    (role, is_staff, is_superuser...) no esta declarado y DRF lo descarta, de
    modo que el registro publico nunca puede elegir su rol ni sus privilegios.
    """

    email = serializers.EmailField(max_length=LONGITUD_MAX_EMAIL)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128
    )
    full_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150, trim_whitespace=True
    )

    def to_internal_value(self, data):
        # El formulario del frontend envia el nombre como "fullName".
        if isinstance(data, Mapping) and "fullName" in data and "full_name" not in data:
            data = {**dict(data.items()), "full_name": data["fullName"]}
        return super().to_internal_value(data)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        # El email es tambien el username: se revisan ambos sin distinguir
        # mayusculas, porque auth.User no obliga a que el email sea unico.
        if (
            User.objects.filter(email__iexact=email).exists()
            or User.objects.filter(username__iexact=email).exists()
        ):
            raise serializers.ValidationError(EMAIL_DUPLICADO)
        return email

    def validate(self, attrs):
        # Con un usuario candidato, para que el validador de similitud compare
        # la contrasena contra el email.
        candidato = User(username=attrs["email"], email=attrs["email"])
        try:
            validate_password(attrs["password"], user=candidato)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        email = validated_data["email"]
        try:
            with transaction.atomic():
                usuario = User.objects.create_user(
                    username=email, email=email, password=validated_data["password"]
                )
                # El perfil lo crea la senal; aqui se fija el rol de forma
                # explicita para que no dependa de ningun valor por defecto.
                perfil = usuario.perfil
                perfil.role = Rol.CLIENTE
                perfil.full_name = validated_data.get("full_name", "")
                perfil.save()
        except IntegrityError as exc:
            # Otro registro gano la carrera despues de validate_email.
            raise serializers.ValidationError({"email": [EMAIL_DUPLICADO]}) from exc
        return usuario


class LoginSerializer(serializers.Serializer):
    """Payload de POST /api/v1/auth/login: email y password.

    Valida las credenciales y deja el usuario en validated_data["user"]. Un
    correo inexistente, ambiguo o una contrasena incorrecta producen el mismo
    401, para no revelar que cuentas existen.
    """

    email = serializers.EmailField(max_length=LONGITUD_MAX_EMAIL)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128
    )

    def validate(self, attrs):
        usuario = self._autenticar(attrs["email"].lower(), attrs["password"])
        if usuario is None:
            raise CredencialesInvalidas()
        attrs["user"] = usuario
        return attrs

    def _autenticar(self, email: str, password: str):
        # Se busca por el campo email (y no por username) para que tambien
        # entren cuentas cuyo username no es el correo, como un superusuario.
        candidatos = list(User.objects.filter(email__iexact=email)[:2])
        if len(candidatos) != 1:
            # Sin cuenta, o con correo repetido (dato heredado): se hashea igual
            # para que el tiempo de respuesta no delate si el correo existe.
            User().set_password(password)
            return None
        # authenticate respeta is_active: un usuario inactivo devuelve None.
        return authenticate(
            request=self.context.get("request"),
            username=candidatos[0].get_username(),
            password=password,
        )
