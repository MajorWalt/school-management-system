from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "staff"

    def ready(self):
        from watson import search as watson

        from . import signals  # noqa: F401

        Staff = self.get_model("Staff")
        watson.register(
            Staff,
            fields=("user__first_name", "user__last_name", "user__email"),
        )
        pass