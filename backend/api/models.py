from django.db import models

class WeatherData(models.Model):
    SOURCE_CHOICES = [
        ('API', 'Open-Meteo History'),
        ('MANUAL', 'Manual Input'),
        ('BMKG', 'BMKG Open Data'),
        ('CSV_IMPORT', 'Uploaded CSV'),
        ('PREDICTION', 'ML Prediction'),
    ]

    timestamp = models.DateTimeField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    pressure = models.FloatField()
    wind_speed = models.FloatField()
    rainfall = models.FloatField(default=0.0)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    def __str__(self):
        return f"{self.timestamp} - {self.source}"