from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    # Root URL Redirection
    path('', lambda request: redirect('/accounts/login/')),
    
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('students/', include('students.urls')),
    path('attendance/', include('attendance.urls')),
    path('events/', include('events.urls')),
    path('certificates/', include('certificates.urls')),
    
    # 📌 Production (Vercel) वर Media Files आणि Static Files सर्व्ह करण्यासाठी:
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]