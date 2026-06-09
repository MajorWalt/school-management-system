from functools import wraps
from django.http import Http404


def tenant_required(view_func):
	@wraps(view_func)
	def wrapper(request, *args, **kwargs):
		if not getattr(request, "school", None):
			raise Http404("No tenant found for this request")
		return view_func(request, *args, **kwargs)
	return wrapper