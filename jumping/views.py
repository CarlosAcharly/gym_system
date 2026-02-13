from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.paginator import Paginator

from users.decorators import allowed_roles
from clients.models import Client
from .models import JumpingClass, Location, Instructor, ClassBooking, Equipment
from .forms import JumpingClassForm, ClassBookingForm, InstructorForm, LocationForm

# ============================================
# DASHBOARD
# ============================================

@login_required
@allowed_roles(['admin', 'recep'])
def dashboard(request):
    """Dashboard principal de Jumping"""
    today = timezone.now().date()
    
    # Clases de hoy
    today_classes = JumpingClass.objects.filter(
        date=today,
        status__in=['scheduled', 'in_progress']
    ).select_related('instructor', 'location')[:10]
    
    # Estadísticas
    total_classes_today = today_classes.count()
    total_bookings_today = ClassBooking.objects.filter(
        jumping_class__date=today,
        status='confirmed'
    ).count()
    
    # Próximas clases
    upcoming_classes = JumpingClass.objects.filter(
        date__gte=today,
        status='scheduled'
    ).order_by('date', 'start_time')[:5]
    
    # Instructores activos
    active_instructors = Instructor.objects.filter(active=True).count()
    
    # Ubicaciones activas
    active_locations = Location.objects.filter(is_active=True).count()
    
    # Reservas pendientes
    pending_bookings = ClassBooking.objects.filter(
        jumping_class__date__gte=today,
        status='confirmed',
        payment_status=False
    ).count()
    
    context = {
        'today_classes': today_classes,
        'total_classes_today': total_classes_today,
        'total_bookings_today': total_bookings_today,
        'upcoming_classes': upcoming_classes,
        'active_instructors': active_instructors,
        'active_locations': active_locations,
        'pending_bookings': pending_bookings,
    }
    return render(request, 'jumping/dashboard.html', context)

# ============================================
# CLASES
# ============================================

@login_required
@allowed_roles(['admin', 'recep'])
def class_list(request):
    """Lista de clases con filtros"""
    date_filter = request.GET.get('date', timezone.now().date())
    location_filter = request.GET.get('location', '')
    instructor_filter = request.GET.get('instructor', '')
    difficulty_filter = request.GET.get('difficulty', '')
    status_filter = request.GET.get('status', '')
    
    classes = JumpingClass.objects.select_related('instructor', 'location').all()
    
    if date_filter:
        classes = classes.filter(date=date_filter)
    if location_filter:
        classes = classes.filter(location_id=location_filter)
    if instructor_filter:
        classes = classes.filter(instructor_id=instructor_filter)
    if difficulty_filter:
        classes = classes.filter(difficulty=difficulty_filter)
    if status_filter:
        classes = classes.filter(status=status_filter)
    
    classes = classes.order_by('date', 'start_time')
    
    # Paginación
    paginator = Paginator(classes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'locations': Location.objects.filter(is_active=True),
        'instructors': Instructor.objects.filter(active=True),
        'filters': {
            'date': date_filter,
            'location': location_filter,
            'instructor': instructor_filter,
            'difficulty': difficulty_filter,
            'status': status_filter,
        }
    }
    return render(request, 'jumping/class_list.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def class_detail(request, pk):
    """Detalle de clase"""
    jumping_class = get_object_or_404(
        JumpingClass.objects.select_related('instructor', 'location'),
        pk=pk
    )
    
    # Reservas de esta clase
    bookings = ClassBooking.objects.filter(
        jumping_class=jumping_class
    ).select_related('client').order_by('booking_date')
    
    # Actualizar estado automáticamente
    jumping_class.update_status()
    
    context = {
        'class': jumping_class,
        'bookings': bookings,
        'available_spots': jumping_class.available_spots,
        'is_full': jumping_class.is_full,
    }
    return render(request, 'jumping/class_detail.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def class_create(request):
    """Crear nueva clase"""
    if request.method == 'POST':
        form = JumpingClassForm(request.POST)
        if form.is_valid():
            jumping_class = form.save()
            
            # Si es recurrente, crear las clases repetidas
            if form.cleaned_data.get('recurring'):
                create_recurring_classes(jumping_class, form.cleaned_data)
            
            messages.success(request, f'Clase {jumping_class.name} creada exitosamente')
            return redirect('jumping:class_detail', pk=jumping_class.pk)
    else:
        form = JumpingClassForm(initial={
            'date': timezone.now().date(),
            'duration': 60,
            'capacity': 20,
        })
    
    context = {
        'form': form,
        'is_edit': False
    }
    return render(request, 'jumping/class_form.html', context)

def create_recurring_classes(base_class, cleaned_data):
    """Crea clases recurrentes"""
    current_date = base_class.date
    end_date = cleaned_data.get('recurring_until')
    recurring_days = cleaned_data.get('recurring_days', [])
    
    if not end_date:
        return
    
    while current_date <= end_date:
        if current_date.weekday() in recurring_days and current_date != base_class.date:
            JumpingClass.objects.create(
                name=base_class.name,
                description=base_class.description,
                instructor=base_class.instructor,
                location=base_class.location,
                date=current_date,
                start_time=base_class.start_time,
                end_time=base_class.end_time,
                duration=base_class.duration,
                capacity=base_class.capacity,
                difficulty=base_class.difficulty,
                price=base_class.price,
                requires_equipment=base_class.requires_equipment,
                equipment_available=base_class.equipment_available,
                recurring=True
            )
        current_date += timedelta(days=1)

@login_required
@allowed_roles(['admin', 'recep'])
def class_edit(request, pk):
    """Editar clase"""
    jumping_class = get_object_or_404(JumpingClass, pk=pk)
    
    if request.method == 'POST':
        form = JumpingClassForm(request.POST, instance=jumping_class)
        if form.is_valid():
            form.save()
            messages.success(request, f'Clase {jumping_class.name} actualizada')
            return redirect('jumping:class_detail', pk=jumping_class.pk)
    else:
        form = JumpingClassForm(instance=jumping_class)
    
    context = {
        'form': form,
        'is_edit': True,
        'class': jumping_class
    }
    return render(request, 'jumping/class_form.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def class_delete(request, pk):
    """Eliminar clase"""
    jumping_class = get_object_or_404(JumpingClass, pk=pk)
    
    if request.method == 'POST':
        class_name = jumping_class.name
        jumping_class.delete()
        messages.success(request, f'Clase {class_name} eliminada')
        return redirect('jumping:class_list')
    
    return render(request, 'jumping/class_confirm_delete.html', {'class': jumping_class})

@login_required
@allowed_roles(['admin', 'recep'])
def class_cancel(request, pk):
    """Cancelar clase"""
    jumping_class = get_object_or_404(JumpingClass, pk=pk)
    
    if request.method == 'POST':
        if jumping_class.can_cancel:
            jumping_class.status = 'cancelled'
            jumping_class.save()
            
            # Notificar a clientes con reservas
            notify_cancelled_class(jumping_class)
            
            messages.warning(request, f'Clase {jumping_class.name} cancelada')
        else:
            messages.error(request, 'No se puede cancelar esta clase')
        
        return redirect('jumping:class_detail', pk=jumping_class.pk)
    
    return render(request, 'jumping/class_confirm_cancel.html', {'class': jumping_class})

# ============================================
# RESERVAS
# ============================================

@login_required
@allowed_roles(['admin', 'recep'])
def create_booking(request, pk):
    """Crear reserva para una clase"""
    jumping_class = get_object_or_404(JumpingClass, pk=pk)
    
    if jumping_class.is_full:
        messages.error(request, 'La clase está completa')
        return redirect('jumping:class_detail', pk=pk)
    
    if request.method == 'POST':
        form = ClassBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.jumping_class = jumping_class
            booking.created_by = request.user
            
            # Verificar si ya tiene reserva
            existing_booking = ClassBooking.objects.filter(
                client=booking.client,
                jumping_class=jumping_class
            ).first()
            
            if existing_booking:
                messages.error(request, 'Este cliente ya tiene reserva para esta clase')
                return redirect('jumping:class_detail', pk=pk)
            
            booking.save()
            
            # Actualizar contador de participantes
            jumping_class.current_participants += 1
            jumping_class.save()
            
            messages.success(request, f'Reserva creada para {booking.client}')
            return redirect('jumping:class_detail', pk=pk)
    else:
        form = ClassBookingForm(initial={
            'payment_status': True,
            'amount_paid': jumping_class.price
        })
    
    context = {
        'form': form,
        'class': jumping_class
    }
    return render(request, 'jumping/booking_form.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def booking_list(request):
    """Lista de reservas"""
    date_from = request.GET.get('from', timezone.now().date())
    date_to = request.GET.get('to', timezone.now().date() + timedelta(days=30))
    status = request.GET.get('status', '')
    
    bookings = ClassBooking.objects.select_related(
        'client', 'jumping_class', 'jumping_class__location'
    ).filter(
        jumping_class__date__range=[date_from, date_to]
    )
    
    if status:
        bookings = bookings.filter(status=status)
    
    bookings = bookings.order_by('-booking_date')
    
    context = {
        'bookings': bookings,
        'date_from': date_from,
        'date_to': date_to,
        'status': status
    }
    return render(request, 'jumping/booking_list.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def cancel_booking(request, pk):
    """Cancelar reserva"""
    booking = get_object_or_404(ClassBooking, pk=pk)
    
    if request.method == 'POST':
        if booking.status != 'cancelled':
            booking.cancel_booking()
            messages.warning(request, 'Reserva cancelada')
        
        return redirect('jumping:class_detail', pk=booking.jumping_class.pk)
    
    return render(request, 'jumping/booking_confirm_cancel.html', {'booking': booking})

@login_required
@allowed_roles(['admin', 'recep'])
def mark_attendance(request, pk):
    """Marcar asistencia"""
    booking = get_object_or_404(ClassBooking, pk=pk)
    
    if request.method == 'POST':
        booking.confirm_attendance()
        messages.success(request, f'Asistencia confirmada para {booking.client}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        return redirect('jumping:class_detail', pk=booking.jumping_class.pk)
    
    return JsonResponse({'status': 'error'}, status=400)

# ============================================
# INSTRUCTORES
# ============================================

@login_required
@allowed_roles(['admin'])
def instructor_list(request):
    """Lista de instructores"""
    instructors = Instructor.objects.all().annotate(
        total_classes=Count('classes'),
        upcoming_classes=Count(
            'classes',
            filter=Q(classes__date__gte=timezone.now().date(), 
                    classes__status='scheduled')
        )
    )
    return render(request, 'jumping/instructor_list.html', {'instructors': instructors})

@login_required
@allowed_roles(['admin'])
def instructor_create(request):
    """Crear instructor"""
    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES)
        if form.is_valid():
            instructor = form.save()
            messages.success(request, f'Instructor {instructor.full_name} creado')
            return redirect('jumping:instructor_list')
    else:
        form = InstructorForm()
    
    return render(request, 'jumping/instructor_form.html', {'form': form})

@login_required
@allowed_roles(['admin'])
def instructor_edit(request, pk):
    """Editar instructor"""
    instructor = get_object_or_404(Instructor, pk=pk)
    
    if request.method == 'POST':
        form = InstructorForm(request.POST, request.FILES, instance=instructor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Instructor {instructor.full_name} actualizado')
            return redirect('jumping:instructor_list')
    else:
        form = InstructorForm(instance=instructor)
    
    return render(request, 'jumping/instructor_form.html', {'form': form, 'instructor': instructor})

@login_required
@allowed_roles(['admin'])
def instructor_delete(request, pk):
    """Eliminar instructor"""
    instructor = get_object_or_404(Instructor, pk=pk)
    
    if request.method == 'POST':
        # Verificar si tiene clases asociadas
        has_classes = JumpingClass.objects.filter(instructor=instructor).exists()
        
        if has_classes:
            messages.error(request, f'No se puede eliminar {instructor.full_name} porque tiene clases asignadas')
        else:
            instructor_name = instructor.full_name
            instructor.delete()
            messages.success(request, f'Instructor {instructor_name} eliminado')
        
        return redirect('jumping:instructor_list')
    
    return render(request, 'jumping/instructor_confirm_delete.html', {'instructor': instructor})

# ============================================
# UBICACIONES
# ============================================

@login_required
@allowed_roles(['admin'])
def location_list(request):
    """Lista de ubicaciones"""
    locations = Location.objects.all().annotate(
        total_classes=Count('classes'),
        active_classes=Count(
            'classes',
            filter=Q(classes__date__gte=timezone.now().date(), 
                    classes__status='scheduled')
        )
    )
    return render(request, 'jumping/location_list.html', {'locations': locations})

@login_required
@allowed_roles(['admin'])
def location_create(request):
    """Crear ubicación"""
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()
            messages.success(request, f'Ubicación {location.name} creada')
            return redirect('jumping:location_list')
    else:
        form = LocationForm()
    
    return render(request, 'jumping/location_form.html', {'form': form})

@login_required
@allowed_roles(['admin'])
def location_edit(request, pk):
    """Editar ubicación"""
    location = get_object_or_404(Location, pk=pk)
    
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ubicación {location.name} actualizada')
            return redirect('jumping:location_list')
    else:
        form = LocationForm(instance=location)
    
    return render(request, 'jumping/location_form.html', {'form': form, 'location': location})

@login_required
@allowed_roles(['admin'])
def location_delete(request, pk):
    """Eliminar ubicación"""
    location = get_object_or_404(Location, pk=pk)
    
    if request.method == 'POST':
        # Verificar si tiene clases asociadas
        has_classes = JumpingClass.objects.filter(location=location).exists()
        
        if has_classes:
            messages.error(request, f'No se puede eliminar {location.name} porque tiene clases programadas')
        else:
            location_name = location.name
            location.delete()
            messages.success(request, f'Ubicación {location_name} eliminada')
        
        return redirect('jumping:location_list')
    
    return render(request, 'jumping/location_confirm_delete.html', {'location': location})

# ============================================
# CALENDARIO Y REPORTES
# ============================================

@login_required
@allowed_roles(['admin', 'recep'])
def class_calendar(request):
    """Vista de calendario"""
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    classes = JumpingClass.objects.filter(
        date__range=[start_date, end_date],
        status__in=['scheduled', 'in_progress', 'full']
    ).select_related('instructor', 'location')
    
    context = {
        'classes': classes,
        'month': month,
        'year': year,
        'month_name': start_date.strftime('%B').capitalize(),
        'locations': Location.objects.filter(is_active=True),
        'instructors': Instructor.objects.filter(active=True),
    }
    return render(request, 'jumping/calendar.html', context)

@login_required
@allowed_roles(['admin'])
def class_report(request):
    """Reporte de clases"""
    start_date = request.GET.get('start', timezone.now().date() - timedelta(days=30))
    end_date = request.GET.get('end', timezone.now().date())
    
    classes = JumpingClass.objects.filter(date__range=[start_date, end_date])
    
    # Estadísticas
    total_classes = classes.count()
    total_bookings = ClassBooking.objects.filter(
        jumping_class__in=classes
    ).count()
    total_revenue = ClassBooking.objects.filter(
        jumping_class__in=classes,
        payment_status=True
    ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    
    # Clases por instructor
    classes_by_instructor = classes.values(
        'instructor__first_name', 'instructor__last_name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Clases por ubicación
    classes_by_location = classes.values(
        'location__name'
    ).annotate(count=Count('id')).order_by('-count')
    
    # Asistencia
    attendance_rate = 0
    if total_bookings > 0:
        attended = ClassBooking.objects.filter(
            jumping_class__in=classes,
            status='attended'
        ).count()
        attendance_rate = (attended / total_bookings) * 100 if total_bookings > 0 else 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_classes': total_classes,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'classes_by_instructor': classes_by_instructor,
        'classes_by_location': classes_by_location,
        'attendance_rate': round(attendance_rate, 2),
    }
    return render(request, 'jumping/report.html', context)

@login_required
@allowed_roles(['admin', 'recep'])
def weekly_schedule(request):
    """Horario semanal"""
    week_offset = int(request.GET.get('week', 0))
    start_date = timezone.now().date() + timedelta(weeks=week_offset)
    start_of_week = start_date - timedelta(days=start_date.weekday())
    
    week_days = []
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        day_classes = JumpingClass.objects.filter(
            date=day_date,
            status__in=['scheduled', 'in_progress', 'full']
        ).select_related('instructor', 'location').order_by('start_time')
        
        week_days.append({
            'date': day_date,
            'day_name': day_date.strftime('%A').capitalize(),
            'classes': day_classes,
            'total_classes': day_classes.count(),
            'total_capacity': sum(c.capacity for c in day_classes),
            'total_booked': sum(c.current_participants for c in day_classes),
        })
    
    context = {
        'week_days': week_days,
        'week_offset': week_offset,
        'week_range': f"{start_of_week.strftime('%d/%m')} - {(start_of_week + timedelta(days=6)).strftime('%d/%m/%Y')}",
        'locations': Location.objects.filter(is_active=True),
    }
    return render(request, 'jumping/weekly_schedule.html', context)

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def notify_cancelled_class(jumping_class):
    """Notifica a los clientes sobre la cancelación"""
    bookings = ClassBooking.objects.filter(
        jumping_class=jumping_class,
        status='confirmed'
    ).select_related('client')
    
    for booking in bookings:
        # Aquí implementarías el envío de SMS/Email
        # Por ahora solo marcamos la reserva como cancelada
        booking.status = 'cancelled'
        booking.save()
        
        print(f"Notificación enviada a {booking.client.phone} - Clase cancelada")