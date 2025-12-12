from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sync-data/', views.fetch_historical_data, name='fetch_historical_data'),
    path('sync-bmkg/', views.fetch_bmkg_data, name='fetch_bmkg_data'),
    path('import-csv/', views.import_csv, name='import_csv'),
    path('train-model/', views.train_model, name='train_model'),
]