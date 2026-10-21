from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "students"

    def ready(self):
        from watson import search as watson

        Student = self.get_model("Student")
        watson.register(
            Student,
            fields=("first_name", "last_name", "student_id"),
        )
        pass