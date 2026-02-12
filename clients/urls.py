from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('create/', views.client_create, name='client_create'),
    path('edit/<int:pk>/', views.client_edit, name='client_edit'),
    path('delete/<int:pk>/', views.client_delete, name='client_delete'),
    path('soft-delete/<int:pk>/', views.client_soft_delete, name='client_soft_delete'),
    path('restore/<int:pk>/', views.client_restore, name='client_restore'),
    path('permanent-delete/<int:pk>/', views.client_permanent_delete, name='client_permanent_delete'),
    path('trash/', views.client_trash, name='client_trash'),
    path('sms/<int:pk>/', views.send_client_sms, name='send_client_sms'),
    path('renew/<int:pk>/', views.renew_membership, name='renew_membership'),
    path('bulk-sms/', views.bulk_sms, name='bulk_sms'),
    path('check-payments/', views.check_overdue_payments, name='check_payments'),
]