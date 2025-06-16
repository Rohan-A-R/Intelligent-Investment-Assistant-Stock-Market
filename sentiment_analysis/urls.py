from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.sentiment_dashboard, name='sentiment_dashboard'),
]