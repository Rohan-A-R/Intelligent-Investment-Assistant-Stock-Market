from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/', views.stock_dashboard, name='stock_dashboard'),
]