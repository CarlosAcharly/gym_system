from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from clients.models import Client
from users.models import User

class Instructor(models.Model):
    """Modelo para instructores/profesores"""
    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido")
    phone = models.CharField(max_length=15, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    specialization = models.CharField(max_length=200, blank=True, verbose_name="Especialización")
    bio = models.TextField(blank=True, verbose_name="Biografía")
    photo = models.ImageField(upload_to='instructors/', blank=True, null=True, verbose_name="Foto")
    active = models.BooleanField(default=True, verbose_name="Activo")
    hire_date = models.DateField(default=timezone.now, verbose_name="Fecha de contratación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructores"
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Location(models.Model):
    """Modelo para ubicaciones/sedes"""
    name = models.CharField(max_length=100, verbose_name="Nombre")
    address = models.TextField(verbose_name="Dirección")
    phone = models.CharField(max_length=15, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    capacity = models.PositiveIntegerField(default=20, verbose_name="Capacidad máxima")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    opening_time = models.TimeField(default="06:00", verbose_name="Hora apertura")
    closing_time = models.TimeField(default="22:00", verbose_name="Hora cierre")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class JumpingClass(models.Model):
    """Modelo para clases de Jumping"""
    STATUS_CHOICES = (
        ('scheduled', 'Programada'),
        ('in_progress', 'En curso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('full', 'Completa'),
    )
    
    DIFFICULTY_CHOICES = (
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('all', 'Todos los niveles'),
    )
    
    name = models.CharField(max_length=100, verbose_name="Nombre de la clase")
    description = models.TextField(blank=True, verbose_name="Descripción")
    instructor = models.ForeignKey(
        Instructor, 
        on_delete=models.CASCADE, 
        related_name='classes',
        verbose_name="Instructor"
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        related_name='classes',
        verbose_name="Ubicación"
    )
    date = models.DateField(verbose_name="Fecha")
    start_time = models.TimeField(verbose_name="Hora inicio")
    end_time = models.TimeField(verbose_name="Hora fin")
    duration = models.PositiveIntegerField(
        default=60, 
        verbose_name="Duración (minutos)"
    )
    capacity = models.PositiveIntegerField(
        default=20, 
        validators=[MinValueValidator(1)],
        verbose_name="Capacidad máxima"
    )
    current_participants = models.PositiveIntegerField(
        default=0,
        verbose_name="Participantes actuales"
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='all',
        verbose_name="Dificultad"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name="Estado"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=150.00,
        verbose_name="Precio"
    )
    requires_equipment = models.BooleanField(
        default=True,
        verbose_name="Requiere equipo"
    )
    equipment_available = models.PositiveIntegerField(
        default=15,
        verbose_name="Equipos disponibles"
    )
    recurring = models.BooleanField(default=False, verbose_name="Clase recurrente")
    recurring_days = models.JSONField(default=list, blank=True, verbose_name="Días de repetición")
    recurring_until = models.DateField(blank=True, null=True, verbose_name="Repetir hasta")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Clase de Jumping"
        verbose_name_plural = "Clases de Jumping"
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['location', 'date']),
            models.Index(fields=['instructor', 'date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.date} {self.start_time} ({self.location})"
    
    @property
    def available_spots(self):
        """Calcula lugares disponibles"""
        return self.capacity - self.current_participants
    
    @property
    def is_full(self):
        """Verifica si la clase está llena"""
        return self.current_participants >= self.capacity
    
    @property
    def can_cancel(self):
        """Verifica si la clase puede cancelarse"""
        return self.status in ['scheduled', 'full'] and self.date >= timezone.now().date()
    
    def update_status(self):
        """Actualiza estado automático"""
        now = timezone.now()
        if self.date < now.date():
            self.status = 'completed'
        elif self.date == now.date() and self.start_time <= now.time() <= self.end_time:
            self.status = 'in_progress'
        elif self.is_full:
            self.status = 'full'
        elif self.status == 'cancelled':
            pass  # Mantener cancelado
        else:
            self.status = 'scheduled'
        self.save()

class ClassBooking(models.Model):
    """Modelo para reservas de clases"""
    STATUS_CHOICES = (
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada'),
        ('attended', 'Asistió'),
        ('no_show', 'No asistió'),
    )
    
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='jumping_bookings',
        verbose_name="Cliente"
    )
    jumping_class = models.ForeignKey(
        JumpingClass,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Clase"
    )
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha reserva")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed',
        verbose_name="Estado"
    )
    payment_status = models.BooleanField(default=False, verbose_name="Pagado")
    payment_date = models.DateTimeField(blank=True, null=True, verbose_name="Fecha pago")
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Monto pagado"
    )
    attended = models.BooleanField(default=False, verbose_name="Asistió")
    check_in_time = models.DateTimeField(blank=True, null=True, verbose_name="Hora de llegada")
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bookings',
        verbose_name="Registrado por"
    )
    
    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        unique_together = ['client', 'jumping_class']  # Un cliente no puede reservar la misma clase dos veces
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['jumping_class', 'status']),
        ]
    
    def __str__(self):
        return f"{self.client} - {self.jumping_class}"
    
    def confirm_attendance(self):
        """Confirma asistencia"""
        self.attended = True
        self.status = 'attended'
        self.check_in_time = timezone.now()
        self.save()
    
    def cancel_booking(self):
        """Cancela la reserva"""
        self.status = 'cancelled'
        self.save()
        
        # Liberar cupo
        class_obj = self.jumping_class
        class_obj.current_participants -= 1
        class_obj.save()

class Equipment(models.Model):
    """Modelo para equipamiento"""
    EQUIPMENT_TYPE = (
        ('jumping', 'Cama elástica'),
        ('mat', 'Colchoneta'),
        ('weight', 'Pesa'),
        ('other', 'Otro'),
    )
    
    CONDITION_CHOICES = (
        ('excellent', 'Excelente'),
        ('good', 'Bueno'),
        ('fair', 'Regular'),
        ('poor', 'Malo'),
        ('damaged', 'Dañado'),
    )
    
    name = models.CharField(max_length=100, verbose_name="Nombre")
    type = models.CharField(max_length=20, choices=EQUIPMENT_TYPE, verbose_name="Tipo")
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        related_name='equipment',
        verbose_name="Ubicación"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    available_quantity = models.PositiveIntegerField(default=1, verbose_name="Disponibles")
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='good',
        verbose_name="Condición"
    )
    last_maintenance = models.DateField(blank=True, null=True, verbose_name="Último mantenimiento")
    next_maintenance = models.DateField(blank=True, null=True, verbose_name="Próximo mantenimiento")
    notes = models.TextField(blank=True, verbose_name="Notas")
    
    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    @property
    def is_available(self):
        return self.available_quantity > 0