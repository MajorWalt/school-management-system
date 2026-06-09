def log_activity(request, action, description):
	"""
	Call this from any view to log a staff action.
	Silently skips if no school or user on the request.
	"""
	try:
		from core.models import ActivityLog
		school = getattr(request, "school", None)
		user   = request.user if request.user.is_authenticated else None
		if not school or not user:
			return

		# Don't log student actions
		from accounts.models import UserRole
		roles = list(UserRole.objects.filter(
			user=user, school=school
		).values_list("role", flat=True))

		if roles == ["student"]:
			return

		ip = (
			request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
			or request.META.get("REMOTE_ADDR")
		)

		ActivityLog.objects.create(
			school      = school,
			user        = user,
			action      = action,
			description = description,
			ip_address  = ip or None,
		)
	except Exception:
		pass  