from django.core.cache import cache
from django.http import Http404
from .models import School


class TenantMiddleware:

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		host = request.get_host().split(":")[0].lower()

		# Bypass middleware for Django admin and local dev
		if host in ("localhost", "127.0.0.1"):
			# Allow django admin through without a tenant
			if request.path.startswith("/django-admin/"):
				request.school         = None
				request.school_profile = None
				return self.get_response(request)

			# For all other paths, load first active school for dev
			school = School.objects.filter(is_active=True).select_related("profile").first()
			request.school         = school
			request.school_profile = getattr(school, "profile", None) if school else None
			return self.get_response(request)

		slug = host.split(".")[0]

		if slug == "admin":
			request.school         = None
			request.school_profile = None
			return self.get_response(request)

		cache_key = f"school_tenant_{slug}"
		school    = cache.get(cache_key)

		if school is None:
			try:
				school = School.objects.select_related("profile").get(
					slug=slug, is_active=True
				)
				cache.set(cache_key, school, 60 * 5)
			except School.DoesNotExist:
				raise Http404("School not found")

		request.school         = school
		request.school_profile = getattr(school, "profile", None)

		return self.get_response(request)