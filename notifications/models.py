from django.db import models
from clients.models import Client

class SMSNotification(models.Model):
    STATUS_CHOICES = (
        ('queued', 'En cola'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('failed', 'Fallido'),
        ('undelivered', 'No entregado'),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    message = models.TextField()
    sid = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} - {self.status}"
