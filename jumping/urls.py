from django.urls import path
from . import views

app_name = 'jumping'

urlpatterns = [
    # Dashboard y vista principal
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # CRUD Clases
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.class_create, name='class_create'),
    path('classes/<int:pk>/', views.class_detail, name='class_detail'),
    path('classes/<int:pk>/edit/', views.class_edit, name='class_edit'),
    path('classes/<int:pk>/delete/', views.class_delete, name='class_delete'),
    path('classes/<int:pk>/cancel/', views.class_cancel, name='class_cancel'),
    
    # Reservas
    path('classes/<int:pk>/book/', views.create_booking, name='create_booking'),
    path('bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('bookings/<int:pk>/attendance/', views.mark_attendance, name='mark_attendance'),
    path('bookings/', views.booking_list, name='booking_list'),
    
    # Instructores
    path('instructors/', views.instructor_list, name='instructor_list'),
    path('instructors/create/', views.instructor_create, name='instructor_create'),
    path('instructors/<int:pk>/edit/', views.instructor_edit, name='instructor_edit'),
    path('instructors/<int:pk>/delete/', views.instructor_delete, name='instructor_delete'),
    
    # Ubicaciones
    path('locations/', views.location_list, name='location_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_edit, name='location_edit'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    
    # Calendario y reportes
    path('calendar/', views.class_calendar, name='class_calendar'),
    path('report/', views.class_report, name='class_report'),
    path('schedule/', views.weekly_schedule, name='weekly_schedule'),
]