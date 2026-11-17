"""Envia los recordatorios de citas: python manage.py enviar_recordatorios.

Pensado para un cron externo (por ejemplo un Cron Job de Render) cada 10 minutos.
Es idempotente: cada cita recibe como maximo un aviso de 24 h y uno de 2 h, por
mas veces que se ejecute. Termina con error solo si hubo fallos de base de datos,
para que el cron falle de forma visible.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.citas.services_recordatorios import enviar_recordatorios


class Command(BaseCommand):
    help = "Envia los recordatorios de 24 h y 2 h de las citas proximas."

    def handle(self, *args, **options):
        resumen = enviar_recordatorios()

        self.stdout.write(f"Enviados: {resumen.enviados}")
        self.stdout.write(f"Fallidos: {resumen.fallidos}")
        self.stdout.write(f"Sin canal (sin correo): {resumen.sin_canal}")
        self.stdout.write(f"Omitidos: {resumen.omitidos}")
        self.stdout.write(f"Errores de base de datos: {resumen.errores}")

        if resumen.errores:
            raise CommandError(
                f"{resumen.errores} cita(s) no se pudieron procesar por errores "
                "de base de datos."
            )
