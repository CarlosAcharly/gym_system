from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Client
from notifications.services import send_sms
from notifications.models import SMSNotification
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_overdue_payments_task():
    """Tarea para verificar pagos vencidos diariamente"""
    try:
        today = timezone.now().date()
        clients = Client.objects.filter(
            is_deleted=False,
            next_payment_date__lt=today,
            payment_status__in=['pending', 'paid']
        )
        
        updated_count = 0
        for client in clients:
            client.update_payment_status()
            updated_count += 1
        
        logger.info(f'Tarea check_overdue_payments: {updated_count} clientes actualizados a vencido')
        return f'{updated_count} clientes actualizados'
        
    except Exception as e:
        logger.error(f'Error en check_overdue_payments_task: {e}')
        return f'Error: {e}'

@shared_task
def send_payment_reminders_task():
    """Enviar recordatorios de pago a clientes"""
    try:
        today = timezone.now().date()
        
        # Clientes con pago vencido (más de 7 días)
        overdue_clients = Client.objects.filter(
            is_deleted=False,
            payment_status='overdue',
            next_payment_date__lt=today - timedelta(days=7),
            active=True
        )
        
        # Clientes con pago próximo (3 días antes)
        upcoming_clients = Client.objects.filter(
            is_deleted=False,
            payment_status='pending',
            next_payment_date=today + timedelta(days=3),
            active=True
        )
        
        total_sent = 0
        
        # Enviar a clientes vencidos
        for client in overdue_clients:
            message = f"Hola {client.first_name}, tu membresía del gimnasio está VENCIDA desde {client.next_payment_date.strftime('%d/%m/%Y')}. Por favor regulariza tu situación para evitar la desactivación."
            
            try:
                sid = send_sms(client.phone, message)
                SMSNotification.objects.create(
                    client=client,
                    message=message,
                    sid=sid,
                    status='sent'
                )
                total_sent += 1
            except Exception as e:
                logger.error(f'Error enviando SMS a {client.phone}: {e}')
        
        # Enviar a clientes con pago próximo
        for client in upcoming_clients:
            message = f"Hola {client.first_name}, tu membresía del gimnasio vence el {client.next_payment_date.strftime('%d/%m/%Y')}. Por favor realiza el pago para continuar disfrutando de nuestros servicios."
            
            try:
                sid = send_sms(client.phone, message)
                SMSNotification.objects.create(
                    client=client,
                    message=message,
                    sid=sid,
                    status='sent'
                )
                total_sent += 1
            except Exception as e:
                logger.error(f'Error enviando SMS a {client.phone}: {e}')
        
        logger.info(f'Tarea send_payment_reminders: {total_sent} SMS enviados')
        return f'{total_sent} recordatorios enviados'
        
    except Exception as e:
        logger.error(f'Error en send_payment_reminders_task: {e}')
        return f'Error: {e}'

@shared_task
def cleanup_recycle_bin_task():
    """Limpiar papelera: eliminar permanentemente después de 30 días"""
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        old_deleted_clients = Client.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        deleted_count = old_deleted_clients.count()
        
        # Eliminar permanentemente
        old_deleted_clients.delete()
        
        logger.info(f'Tarea cleanup_recycle_bin: {deleted_count} clientes eliminados permanentemente')
        return f'{deleted_count} clientes eliminados permanentemente'
        
    except Exception as e:
        logger.error(f'Error en cleanup_recycle_bin_task: {e}')
        return f'Error: {e}'

@shared_task
def deactivate_unpaid_clients_task():
    """Desactivar clientes con pago vencido por más de 15 días"""
    try:
        cutoff_date = timezone.now().date() - timedelta(days=15)
        unpaid_clients = Client.objects.filter(
            is_deleted=False,
            payment_status='overdue',
            next_payment_date__lt=cutoff_date,
            active=True
        )
        
        deactivated_count = 0
        for client in unpaid_clients:
            client.active = False
            client.save()
            deactivated_count += 1
            
            # Enviar notificación de desactivación
            message = f"Hola {client.first_name}, tu membresía del gimnasio ha sido DESACTIVADA por falta de pago. Para reactivar, comunícate con recepción."
            
            try:
                sid = send_sms(client.phone, message)
                SMSNotification.objects.create(
                    client=client,
                    message=message,
                    sid=sid,
                    status='sent'
                )
            except Exception as e:
                logger.error(f'Error enviando SMS de desactivación a {client.phone}: {e}')
        
        logger.info(f'Tarea deactivate_unpaid_clients: {deactivated_count} clientes desactivados')
        return f'{deactivated_count} clientes desactivados'
        
    except Exception as e:
        logger.error(f'Error en deactivate_unpaid_clients_task: {e}')
        return f'Error: {e}'

@shared_task
def renew_monthly_memberships_task():
    """Renovación automática para clientes con pago automático (futura funcionalidad)"""
    # Esto se puede implementar cuando agregues pagos automáticos
    pass