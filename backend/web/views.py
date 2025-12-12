import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from django.shortcuts import render, redirect
from api.models import WeatherData
from django.utils import timezone
from datetime import datetime
from .forms import ManualWeatherForm

def dashboard(request):
    # Handle Input Manual
    if request.method == 'POST':
        form = ManualWeatherForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.source = 'MANUAL'
            instance.timestamp = timezone.now()
            instance.save()
            return redirect('dashboard')
    else:
        form = ManualWeatherForm()

    # Ambil data untuk ditampilkan di tabel/grafik
    latest_data = WeatherData.objects.all().order_by('-timestamp')[:10]

    context = {
        'form': form,
        'latest_data': latest_data
    }
    return render(request, 'dashboard.html', context)

# Setup Open-Meteo Client
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def fetch_historical_data(request):
    # 1. Konfigurasi Lokasi & Waktu (Sesuaikan Lat/Long lokasi Anda)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": -6.2088, # Contoh: Jakarta
        "longitude": 106.8456,
        "start_date": "2020-01-01", # Mengambil data 5 tahun ke belakang
        "end_date": "2024-12-12",
        "hourly": ["temperature_2m", "relative_humidity_2m", "rain", "surface_pressure", "wind_speed_10m"]
    }

    # 2. Request ke API
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    # 3. Proses Data menggunakan Pandas
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_rain = hourly.Variables(2).ValuesAsNumpy()
    hourly_surface_pressure = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}
    
    df = pd.DataFrame(data = hourly_data)
    
    # 4. Simpan ke Database Django (Bulk Create agar cepat)
    weather_objects = []
    for index, row in df.iterrows():
        # Pastikan data lengkap sebelum disimpan
        obj = WeatherData(
            timestamp=row['date'],
            temperature=float(hourly_temperature_2m[index]),
            humidity=float(hourly_relative_humidity_2m[index]),
            rainfall=float(hourly_rain[index]),
            pressure=float(hourly_surface_pressure[index]),
            wind_speed=float(hourly_wind_speed_10m[index]),
            source='API' # Menandai ini data untuk Training
        )
        weather_objects.append(obj)
    
    # Hapus data lama jika perlu, lalu simpan yang baru
    # WeatherData.objects.filter(source='API').delete() 
    WeatherData.objects.bulk_create(weather_objects, ignore_conflicts=True)

    return redirect('dashboard') # Akan diarahkan kembali ke dashboard