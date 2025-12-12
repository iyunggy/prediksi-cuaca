from django import forms
from api.models import WeatherData

class ManualWeatherForm(forms.ModelForm):
    class Meta:
        model = WeatherData
        fields = ['temperature', 'humidity', 'pressure', 'wind_speed', 'rainfall']
        widgets = {
            'temperature': forms.NumberInput(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring focus:border-blue-300'}),
            'humidity': forms.NumberInput(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring focus:border-blue-300'}),
            'pressure': forms.NumberInput(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring focus:border-blue-300'}),
            'wind_speed': forms.NumberInput(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring focus:border-blue-300'}),
            'rainfall': forms.NumberInput(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring focus:border-blue-300'}),
        }