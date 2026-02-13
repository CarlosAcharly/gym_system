from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from users.decorators import allowed_roles
from .models import Client
from notifications.services import send_sms
from notifications.models import SMSNotification
# users/views.py o donde tengas la home view


# users/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from clients.models import Client
from jumping.models import JumpingClass, ClassBooking, Instructor, Location
from notifications.models import SMSNotification
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Sum
from django.conf import settings

@login_required
def home(request):
    """Página principal del dashboard con datos de clientes y jumping"""
    today = timezone.now().date()
    
    # ============================================
    # DATOS DE CLIENTES
    # ============================================
    total_clients_all = Client.objects.count()
    total_clients = Client.objects.filter(is_deleted=False).count()
    overdue_clients = Client.objects.filter(
        is_deleted=False, 
        payment_status='overdue'
    ).count()
    paid_clients = Client.objects.filter(
        is_deleted=False, 
        payment_status='paid'
    ).count()
    deleted_clients = Client.objects.filter(is_deleted=True).count()
    
    # Porcentajes
    overdue_percentage = (overdue_clients / total_clients * 100) if total_clients > 0 else 0
    paid_percentage = (paid_clients / total_clients * 100) if total_clients > 0 else 0
    
    # Próximos vencimientos (7 días)
    upcoming_clients = Client.objects.filter(
        is_deleted=False,
        next_payment_date__gte=today,
        payment_status='pending'
    ).order_by('next_payment_date')[:5]
    
    # Agregar días hasta vencimiento
    for client in upcoming_clients:
        client.days_until_due = (client.next_payment_date - today).days if client.next_payment_date else 0
    
    # ============================================
    # DATOS DE JUMPING
    # ============================================
    # Clases de hoy
    today_jumping_classes = JumpingClass.objects.filter(
        date=today,
        status__in=['scheduled', 'in_progress']
    ).select_related('instructor', 'location')[:5]
    
    jumping_classes_today = today_jumping_classes.count()
    
    # Reservas de hoy
    jumping_bookings_today = ClassBooking.objects.filter(
        jumping_class__date=today,
        status='confirmed'
    ).count()
    
    # Ocupación de hoy
    total_capacity_today = sum(c.capacity for c in today_jumping_classes)
    total_booked_today = sum(c.current_participants for c in today_jumping_classes)
    jumping_occupancy_today = (total_booked_today / total_capacity_today * 100) if total_capacity_today > 0 else 0
    
    # Instructores y ubicaciones activas
    active_instructors = Instructor.objects.filter(active=True).count()
    active_locations = Location.objects.filter(is_active=True).count()
    
    # Próximas clases (próximos 7 días)
    upcoming_jumping_classes = JumpingClass.objects.filter(
        date__gte=today,
        date__lte=today + timedelta(days=7),
        status='scheduled'
    ).select_related('instructor', 'location').order_by('date', 'start_time')[:5]
    
    # ============================================
    # ACTIVIDAD RECIENTE
    # ============================================
    recent_activities = []
    
    # Últimos clientes agregados
    recent_clients = Client.objects.filter(is_deleted=False).order_by('-created_at')[:3]
    for client in recent_clients:
        recent_activities.append({
            'type': 'client',
            'title': f'Nuevo cliente: {client.first_name} {client.last_name}',
            'description': f'Tel: {client.phone}',
            'time': client.created_at.strftime('%H:%M'),
            'user': 'Sistema'
        })
    
    # Últimas reservas
    recent_bookings = ClassBooking.objects.select_related('client', 'jumping_class').order_by('-booking_date')[:3]
    for booking in recent_bookings:
        recent_activities.append({
            'type': 'jumping',
            'title': f'Reserva: {booking.client.first_name} {booking.client.last_name}',
            'description': f'Clase: {booking.jumping_class.name} - {booking.jumping_class.date.strftime("%d/%m")}',
            'time': booking.booking_date.strftime('%H:%M'),
            'user': booking.created_by.username if booking.created_by else 'Sistema'
        })
    
    # Últimos SMS
    recent_sms = SMSNotification.objects.select_related('client').order_by('-created_at')[:3]
    for sms in recent_sms:
        recent_activities.append({
            'type': 'sms',
            'title': f'SMS enviado a {sms.client.first_name} {sms.client.last_name}',
            'description': sms.message[:50] + '...',
            'time': sms.created_at.strftime('%H:%M'),
            'user': 'Sistema'
        })
    
    # Ordenar por tiempo (más reciente primero)
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:5]  # Solo los 5 más recientes
    
    # ============================================
    # ESTADO DEL SISTEMA
    # ============================================
    twilio_connected = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
    
    context = {
        # Clientes
        'total_clients': total_clients,
        'total_clients_all': total_clients_all,
        'overdue_clients': overdue_clients,
        'paid_clients': paid_clients,
        'deleted_clients': deleted_clients,
        'overdue_percentage': round(overdue_percentage, 1),
        'paid_percentage': round(paid_percentage, 1),
        'upcoming_clients': upcoming_clients,
        
        # Jumping
        'today_jumping_classes': today_jumping_classes,
        'jumping_classes_today': jumping_classes_today,
        'jumping_bookings_today': jumping_bookings_today,
        'jumping_occupancy_today': round(jumping_occupancy_today, 1),
        'active_instructors': active_instructors,
        'active_locations': active_locations,
        'upcoming_jumping_classes': upcoming_jumping_classes,
        
        # Actividad
        'recent_activities': recent_activities,
        
        # Sistema
        'twilio_connected': twilio_connected,
    }
    
    return render(request, 'home.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def client_list(request):
    """Lista de clientes activos"""
    clients = Client.objects.filter(is_deleted=False)
    
    # Filtrar por estado de pago si se especifica
    status_filter = request.GET.get('status')
    if status_filter:
        clients = clients.filter(payment_status=status_filter)
    
    # Filtrar por búsqueda
    search_query = request.GET.get('search', '')
    if search_query:
        clients = clients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Contar clientes en papelera
    deleted_count = Client.objects.filter(is_deleted=True).count()
    
    context = {
        'clients': clients,
        'status_filter': status_filter,
        'search_query': search_query,
        'deleted_count': deleted_count,
    }
    return render(request, 'clients/client_list.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def client_trash(request):
    """Papelera de reciclaje"""
    deleted_clients = Client.objects.filter(is_deleted=True)
    return render(request, 'clients/client_trash.html', {'clients': deleted_clients})

@login_required
@allowed_roles(['admin', 'recep'])
def client_create(request):
    """Crear nuevo cliente"""
    if request.method == 'POST':
        client = Client.objects.create(
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            phone=request.POST['phone'],
            email=request.POST.get('email')
        )
        
        # Configurar fechas de pago si se proporcionan
        if request.POST.get('start_date'):
            start_date = timezone.datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
            client.last_payment_date = start_date
            client.next_payment_date = start_date + timedelta(days=30)
            client.save()
        
        messages.success(request, f'Cliente {client} creado exitosamente')
        return redirect('client_list')
    
    return render(request, 'clients/client_form.html')

@login_required
@allowed_roles(['admin', 'recep'])
def client_edit(request, pk):
    """Editar cliente existente"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        client.first_name = request.POST['first_name']
        client.last_name = request.POST['last_name']
        client.phone = request.POST['phone']
        client.email = request.POST.get('email')
        client.active = 'active' in request.POST
        
        # Actualizar fechas si se proporcionan
        if request.POST.get('last_payment_date'):
            try:
                last_date = timezone.datetime.strptime(request.POST['last_payment_date'], '%Y-%m-%d').date()
                client.last_payment_date = last_date
                
                # Si no hay próximo pago, calcular automáticamente
                if not request.POST.get('next_payment_date'):
                    client.next_payment_date = last_date + timedelta(days=30)
            except ValueError:
                pass
        
        if request.POST.get('next_payment_date'):
            try:
                next_date = timezone.datetime.strptime(request.POST['next_payment_date'], '%Y-%m-%d').date()
                client.next_payment_date = next_date
            except ValueError:
                pass
        
        # Actualizar estado de pago
        if request.POST.get('payment_status'):
            client.payment_status = request.POST['payment_status']
        
        client.save()
        messages.success(request, f'Cliente {client} actualizado')
        return redirect('client_list')
    
    return render(request, 'clients/client_form.html', {'client': client})

@login_required
@allowed_roles(['admin', 'recep'])
def client_delete(request, pk):
    """Eliminación suave (a papelera) - Mantener para compatibilidad"""
    return client_soft_delete(request, pk)

@login_required
@allowed_roles(['admin', 'recep'])
def client_soft_delete(request, pk):
    """Eliminación suave (a papelera)"""
    client = get_object_or_404(Client, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        client.soft_delete()
        messages.warning(request, f'Cliente {client} movido a la papelera')
        return redirect('client_list')
    
    return render(request, 'clients/client_confirm_delete.html', {
        'client': client,
        'action': 'soft_delete'
    })

@login_required
@allowed_roles(['admin'])
def client_permanent_delete(request, pk):
    """Eliminación permanente"""
    client = get_object_or_404(Client, pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        client_name = str(client)
        client.delete()
        messages.error(request, f'Cliente {client_name} eliminado permanentemente')
        return redirect('client_trash')
    
    return render(request, 'clients/client_confirm_delete.html', {
        'client': client,
        'action': 'permanent_delete'
    })

@login_required
@allowed_roles(['admin', 'recep'])
def client_restore(request, pk):
    """Restaurar cliente desde la papelera"""
    client = get_object_or_404(Client, pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        client.restore()
        messages.success(request, f'Cliente {client} restaurado')
        return redirect('client_list')
    
    return render(request, 'clients/client_confirm_restore.html', {'client': client})

@login_required
@allowed_roles(['admin', 'recep'])
def send_client_sms(request, pk):
    """Enviar SMS individual"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        message = request.POST['message']
        
        try:
            sid = send_sms(client.phone, message)
            
            SMSNotification.objects.create(
                client=client,
                message=message,
                sid=sid,
                status='sent'
            )
            
            messages.success(request, 'SMS enviado correctamente')
            
        except Exception as e:
            SMSNotification.objects.create(
                client=client,
                message=message,
                status='error'
            )
            messages.error(request, f'Error al enviar SMS: {e}')
        
        return redirect('client_list')
    
    # Mensaje por defecto para recordatorio de pago
    default_message = f"Hola {client.first_name}, recuerda que tu membresía del gimnasio está próxima a vencer. Por favor realiza el pago para mantener tu acceso."
    
    return render(request, 'clients/send_sms.html', {
        'client': client,
        'default_message': default_message
    })

@login_required
@allowed_roles(['admin', 'recep'])
def renew_membership(request, pk):
    """Renovar membresía del cliente"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        client.renew_membership()
        messages.success(request, f'Membresía de {client} renovada por 30 días')
        return redirect('client_list')
    
    return render(request, 'clients/renew_membership.html', {'client': client})

@login_required
@allowed_roles(['admin', 'recep'])
def bulk_sms(request):
    """Enviar SMS masivo a clientes con pago pendiente/vencido"""
    if request.method == 'POST':
        message = request.POST['message']
        client_ids = request.POST.getlist('clients')
        
        clients = Client.objects.filter(
            id__in=client_ids,
            is_deleted=False
        )
        
        success_count = 0
        error_count = 0
        
        for client in clients:
            try:
                sid = send_sms(client.phone, message)
                SMSNotification.objects.create(
                    client=client,
                    message=message,
                    sid=sid,
                    status='sent'
                )
                success_count += 1
            except Exception:
                SMSNotification.objects.create(
                    client=client,
                    message=message,
                    status='error'
                )
                error_count += 1
        
        messages.info(request, f'SMS enviados: {success_count} exitosos, {error_count} fallidos')
        return redirect('client_list')
    
    # Mostrar clientes con pago vencido o pendiente
    overdue_clients = Client.objects.filter(
        is_deleted=False,
        payment_status__in=['overdue', 'pending']
    )
    
    return render(request, 'clients/bulk_sms.html', {'clients': overdue_clients})

@login_required
@allowed_roles(['admin'])
def check_overdue_payments(request):
    """Verificar y actualizar estados de pago vencidos"""
    today = timezone.now().date()
    overdue_clients = Client.objects.filter(
        is_deleted=False,
        next_payment_date__lt=today,
        payment_status__in=['pending', 'paid']
    )
    
    updated_count = 0
    for client in overdue_clients:
        client.update_payment_status()
        if client.payment_status == 'overdue':
            updated_count += 1
    
    messages.info(request, f'Se actualizaron {updated_count} clientes con pago vencido')
    return redirect('client_list')