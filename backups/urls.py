from django.urls import path
from . import views

app_name = "backups"

urlpatterns = [
	path("",                        views.backup_list,     name="list"),
	path("run/",                    views.backup_run,      name="run"),
	path("<int:pk>/download/",      views.backup_download, name="download"),
	path("<int:pk>/delete/",        views.backup_delete,   name="delete"),
]