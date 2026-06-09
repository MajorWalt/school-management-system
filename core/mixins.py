class TenantQueryMixin:
	"""
	Mixin for class-based views.
	Automatically scopes querysets to request.school.
	"""

	def get_queryset(self):
		qs = super().get_queryset()
		if hasattr(self.request, "school") and self.request.school:
			qs = qs.filter(school=self.request.school)
		return qs