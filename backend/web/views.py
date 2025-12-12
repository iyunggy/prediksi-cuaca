import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from django.shortcuts import render, redirect
from django.utils import timezone
from api.models import WeatherData
from .forms import ManualWeatherForm

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def fetch_historical_data(request):
    lat = float(request.GET.get('lat', -6.2088))
    lon = float(request.GET.get('lon', 106.8456))

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2024-01-01",
        "end_date": "2024-12-12",
        "hourly": ["temperature_2m", "relative_humidity_2m", "rain", "surface_pressure", "wind_speed_10m"]
    }

    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_rain = hourly.Variables(2).ValuesAsNumpy()
        hourly_surface_pressure = hourly.Variables(3).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        
        df = pd.DataFrame(data=hourly_data)
        
        weather_objects = []
        for index, row in df.iterrows():
            obj = WeatherData(
                timestamp=row['date'],
                temperature=float(hourly_temperature_2m[index]),
                humidity=float(hourly_relative_humidity_2m[index]),
                rainfall=float(hourly_rain[index]),
                pressure=float(hourly_surface_pressure[index]),
                wind_speed=float(hourly_wind_speed_10m[index]),
                source='API'
            )
            weather_objects.append(obj)
        
        WeatherData.objects.filter(source='API').delete()
        WeatherData.objects.bulk_create(weather_objects, ignore_conflicts=True)
        
    except Exception as e:
        print(f"Error: {e}")

    return redirect('dashboard')

def dashboard(request):
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

    latest_data = WeatherData.objects.all().order_by('-timestamp')[:20]

    context = {
        'form': form,
        'latest_data': latest_data
    }
    return render(request, 'dashboard.html', context)