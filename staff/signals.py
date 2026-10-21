from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def reindex_staff_on_user_save(sender, instance, **kwargs):
    """Keep watson's Staff index in sync when the linked User's name/email changes."""
    if kwargs.get("raw"):
        return
    from watson import search as watson

    from .models import Staff

    for member in Staff.objects.filter(user=instance).select_related("user"):
        watson.default_search_engine.update_obj_index(member)
    pass