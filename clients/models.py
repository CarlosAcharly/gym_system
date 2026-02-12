from django.db import models
from django.utils import timezone

class Client(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    
    # Campos para control de pagos
    last_payment_date = models.DateField(blank=True, null=True)
    next_payment_date = models.DateField(blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('paid', 'Pagado'),
            ('pending', 'Pendiente'),
            ('overdue', 'Vencido'),
        ],
        default='pending'
    )
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def soft_delete(self):
        """Eliminación suave"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restaurar desde la papelera"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()
    
    def update_payment_status(self):
        """Actualizar estado de pago"""
        today = timezone.now().date()
        if self.next_payment_date and self.next_payment_date < today:
            self.payment_status = 'overdue'
            self.save()
    
    def renew_membership(self):
        """Renovar membresía por un mes"""
        today = timezone.now().date()
        self.last_payment_date = today
        self.next_payment_date = today + timezone.timedelta(days=30)
        self.payment_status = 'paid'
        self.active = True
        self.save()
    
    class Meta:
        indexes = [
            models.Index(fields=['is_deleted', 'active']),
            models.Index(fields=['payment_status', 'next_payment_date']),
        ]