from django.contrib import admin
from django.urls import path, include
from users.views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('clients/', include('clients.urls')),
    path('notifications/', include('notifications.urls')),
]
