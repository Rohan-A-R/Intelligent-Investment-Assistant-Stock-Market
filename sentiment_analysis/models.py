from django.db import models

class SentimentAnalysis(models.Model):
    symbol=models.CharField(max_length=30)
    summary=models.TextField()
    recommendation=models.CharField(max_length=2000)
    predicted_price=models.FloatField()
    analysis_date=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.symbol} - {self.analysis_date}"