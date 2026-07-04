from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from core.activity import log_activity


def login_view(request):
    if request.user.is_authenticated:
        return redirect("portals:dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            log_activity(request, "login", f"User {user.email} logged in.")
            return redirect(request.GET.get("next", "portals:dashboard"))
        messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html")


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request, "logout", f"User {request.user.email} logged out.")
    logout(request)
    return redirect("accounts:login")
