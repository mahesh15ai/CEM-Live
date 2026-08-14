from django.urls import path
from . import views

urlpatterns = [
    path('', views.manage_teachers, name='manage_teachers'),
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
]