from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', views.health, name='health'),
    path('store/', views.store, name='store'),
    path('api/signup/', views.api_signup, name='api_signup'),
    path('api/login/', views.api_login, name='api_login'),
    path('deposit/process-payment/', views.process_deposit, name='process_deposit'),
    path('external_api/api/products/', views.products, name='products'),
    path('external_api/api/create_order/', views.create_order_view, name='create_order'),
    path('inventory/upload/', views.inventory_upload, name='inventory_upload'),
    path('inventory/ai-desc/', views.ai_description, name='ai_description'),
]