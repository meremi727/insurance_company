from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name="home"),
    path('contract_types', views.contract_types, name='contract_types'),
    path('contacts', views.contacts, name='contacts'),
    path('about', views.about, name='about'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
]