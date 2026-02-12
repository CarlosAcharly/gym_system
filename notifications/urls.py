from django.urls import path
from .views import sms_status_callback

urlpatterns = [
    path('sms/status/', sms_status_callback, name='sms_status_callback'),
]
