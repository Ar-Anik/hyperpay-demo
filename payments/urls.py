from django.urls import path
from . import views

urlpatterns = [
   path('health/', views.health_check, name='health_check'),

   path('', views.payment_page, name='payment_page'),

   path('create-checkout/', views.create_checkout, name='create_checkout'),

   path('shopper-result/', views.shopper_result, name='shopper_result'),
]

