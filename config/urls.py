"""
URL configuration for ERP Web project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('cadastros/', include('apps.cadastros.urls')),
    path('estoque/', include('apps.estoque.urls')),
    path('fiscal/', include('apps.fiscal.urls')),
    path('', include('apps.core.urls')),  # Home e páginas gerais
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
