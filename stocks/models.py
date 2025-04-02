from django.db import models

class StockPrice(models.Model):
    symbol = models.CharField(max_length=10)  # e.g., "AAPL"
    timestamp = models.DateTimeField()
    open_price = models.FloatField()
    high_price = models.FloatField()
    low_price = models.FloatField()
    close_price = models.FloatField()
    volume = models.IntegerField()

    def __str__(self):
        return f"{self.symbol} - {self.timestamp}"