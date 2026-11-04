from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_del_usuario(sender, instance, created, raw=False, **kwargs):
    """Todo usuario nuevo nace con perfil y rol cliente (excepto al cargar fixtures)."""
    if created and not raw:
        PerfilUsuario.objects.get_or_create(user=instance)
