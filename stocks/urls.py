from django.urls import path
from . import views
from django.shortcuts import redirect


urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('', lambda request: redirect('stock_dashboard')),
    path('dashboard/', views.stock_dashboard, name='stock_dashboard'),
]