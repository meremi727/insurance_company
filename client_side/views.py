from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.contrib.auth import login as Login, logout as Logout, authenticate
from django.http import Http404
from django.core.exceptions import PermissionDenied


def index(request: HttpRequest):
    if request.user is not None and request.user.is_authenticated:
        return redirect("work")
    
    return render(request, "client/index.html")

def contract_types(request: HttpRequest):
    return render(request, "client/contract_types.html")

def contacts(request: HttpRequest):
    return render(request, "client/contacts.html")

def about(request: HttpRequest):
    return render(request, "client/about.html")

def login(request: HttpRequest):
    if request.method != "POST":
        raise Http404(request)
    
    login_ = request.POST.get("login", None)
    password_ = request.POST.get("password", None)
    user = authenticate(request, username=login_, password=password_)
    if user is not None and user.is_active:
        Login(request, user)
        return redirect('work')
    else:
        raise PermissionDenied()

def logout(request: HttpRequest):
    Logout(request)
    return redirect('home')

