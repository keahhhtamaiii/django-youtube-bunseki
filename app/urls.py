from django.urls import path
from app import views
from .views import CallbackView


urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('callback/', CallbackView.as_view(), name='callback'),
]