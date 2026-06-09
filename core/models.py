from django.db import models


class School(models.Model):
	name       = models.CharField(max_length=200)
	slug       = models.SlugField(unique=True)
	is_active  = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "schools"

	def __str__(self):
		return self.name