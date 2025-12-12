# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sync-data/', views.fetch_historical_data, name='fetch_historical_data'),
]