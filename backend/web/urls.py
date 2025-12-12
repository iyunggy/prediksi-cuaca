# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/sunshine/', views.sunshine_control_view, name='sunshine_control'),
]