from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages


def login_view(request):
	if request.user.is_authenticated:
		return redirect("portals:dashboard")

	if request.method == "POST":
		email    = request.POST.get("email", "").strip()
		password = request.POST.get("password", "")
		user     = authenticate(request, email=email, password=password)

		if user is not None:
			login(request, user)
			return redirect(request.GET.get("next", "portals:dashboard"))
		else:
			messages.error(request, "Invalid email or password.")

	return render(request, "accounts/login.html")


def logout_view(request):
	logout(request)
	return redirect("accounts:login")