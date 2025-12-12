# models.py
from django.db import models

class WeatherData(models.Model):
    SOURCE_CHOICES = [
        ('API', 'Open-Meteo History'),
        ('MANUAL', 'Manual Input (Sensor Sim)'),
        ('PREDICTION', 'ML Prediction'),
    ]

    timestamp = models.DateTimeField()
    temperature = models.FloatField()  # Sesuai parameter [cite: 168]
    humidity = models.FloatField()     # Sesuai parameter [cite: 171]
    pressure = models.FloatField()     # Sesuai parameter 
    wind_speed = models.FloatField()   # Sesuai parameter [cite: 174]
    rainfall = models.FloatField(default=0.0)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    def __str__(self):
        return f"{self.timestamp} - {self.source}"