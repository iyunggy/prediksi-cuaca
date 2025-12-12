import openmeteo_requests
import requests_cache
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import urllib3
import numpy as np
from retry_requests import retry
from django.shortcuts import render, redirect
from django.utils import timezone
from api.models import WeatherData
from .forms import ManualWeatherForm
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        df = pd.DataFrame({"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()), inclusive="left")})
        
        df['temperature'] = hourly.Variables(0).ValuesAsNumpy()
        df['humidity'] = hourly.Variables(1).ValuesAsNumpy()
        df['rainfall'] = hourly.Variables(2).ValuesAsNumpy()
        df['pressure'] = hourly.Variables(3).ValuesAsNumpy()
        df['wind_speed'] = hourly.Variables(4).ValuesAsNumpy()

        weather_objects = [
            WeatherData(timestamp=row['date'], temperature=row['temperature'], humidity=row['humidity'],
                        rainfall=row['rainfall'], pressure=row['pressure'], wind_speed=row['wind_speed'], source='API')
            for _, row in df.iterrows()
        ]
        WeatherData.objects.filter(source='API').delete()
        WeatherData.objects.bulk_create(weather_objects, ignore_conflicts=True)
    except Exception:
        pass
    return redirect('dashboard')

def fetch_bmkg_data(request):
    url = "https://data.bmkg.go.id/DataMKG/MEWS/DigitalForecast/DigitalForecast-DKIJakarta.xml"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200 and 'html' not in response.headers.get('Content-Type', '').lower():
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                return redirect('dashboard')
            target_area = None
            for area in root.findall(".//area"):
                if area.get("description") == "Jakarta Pusat": 
                    target_area = area
                    break
            if not target_area and len(root.findall(".//area")) > 0:
                target_area = root.findall(".//area")[0]
            if target_area:
                weather_objects = []
                current_time = timezone.now().replace(minute=0, second=0, microsecond=0)
                def get_value(param_id, hour_index):
                    param = target_area.find(f".//parameter[@id='{param_id}']")
                    if param:
                        timeranges = param.findall("timerange")
                        if len(timeranges) > hour_index:
                            val = timeranges[hour_index].find("value")
                            if val is not None and val.text: return float(val.text)
                    return 0.0
                for i in range(4): 
                    weather_objects.append(WeatherData(
                        timestamp=current_time + timezone.timedelta(hours=i*6),
                        temperature=get_value('t', i), humidity=get_value('hu', i), pressure=1010.0,
                        wind_speed=get_value('ws', i), rainfall=0.0, source='BMKG'
                    ))
                if weather_objects:
                    WeatherData.objects.filter(source='BMKG').delete()
                    WeatherData.objects.bulk_create(weather_objects)
    except Exception:
        pass
    return redirect('dashboard')

def import_csv(request):
    if request.method == "POST" and request.FILES.get('csv_file'):
        try:
            df = pd.read_csv(request.FILES['csv_file'])
            col_map = {'date': 'timestamp', 'time': 'timestamp', 'temp_avg': 'temperature', 'temp': 'temperature', 
                       'rh_avg': 'humidity', 'humidity': 'humidity', 'wind_speed_avg': 'wind_speed', 'ws': 'wind_speed',
                       'rain': 'rainfall', 'rr': 'rainfall', 'surface_pressure': 'pressure'}
            df.rename(columns=lambda x: col_map.get(x, x), inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            weather_objects = []
            for _, row in df.iterrows():
                weather_objects.append(WeatherData(
                    timestamp=row['timestamp'], temperature=float(row['temperature']), humidity=float(row['humidity']),
                    pressure=float(row.get('pressure', 1010.0)), wind_speed=float(row.get('wind_speed', 0.0)),
                    rainfall=float(row.get('rainfall', 0.0)), source='CSV_IMPORT'
                ))
            WeatherData.objects.filter(source='CSV_IMPORT').delete()
            WeatherData.objects.bulk_create(weather_objects)
        except Exception: pass
    return redirect('dashboard')

def train_model(request):
    data = WeatherData.objects.exclude(source='PREDICTION').exclude(source='BMKG').values()
    df = pd.DataFrame(list(data))
    if df.empty or len(df) < 20:
        return redirect('dashboard')

    df = df.sort_values('timestamp')
    df['target_temp'] = df['temperature'].shift(-1)
    df_clean = df.dropna(subset=['target_temp'])
    
    features = ['temperature', 'humidity', 'pressure', 'wind_speed', 'rainfall']
    X = df_clean[features]
    y = df_clean['target_temp']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred) * 100

    request.session['model_r2'] = round(r2, 2)
    request.session['model_mae'] = round(mae, 2)
    request.session['model_rmse'] = round(rmse, 2)

    last_real_data = df.iloc[-1][features].to_frame().T
    last_data_scaled = scaler.transform(last_real_data)
    future_temp = model.predict(last_data_scaled)[0]
    future_time = df.iloc[-1]['timestamp'] + timezone.timedelta(hours=1)
    
    WeatherData.objects.filter(source='PREDICTION').delete()
    WeatherData.objects.create(
        timestamp=future_time,
        temperature=future_temp,
        humidity=last_real_data['humidity'].values[0],
        pressure=last_real_data['pressure'].values[0],
        wind_speed=last_real_data['wind_speed'].values[0],
        rainfall=0.0,
        source='PREDICTION'
    )
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

    latest_data = WeatherData.objects.all().order_by('-timestamp')[:50]
    prediction = WeatherData.objects.filter(source='PREDICTION').first()

    context = {
        'form': form,
        'latest_data': latest_data,
        'prediction': prediction,
        'r2_score': request.session.get('model_r2', '-'),
        'mae_score': request.session.get('model_mae', '-'),
        'rmse_score': request.session.get('model_rmse', '-')
    }
    return render(request, 'dashboard.html', context)