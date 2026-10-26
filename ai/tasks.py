from celery import shared_task
from core.models import School
from accounts.models import User
from .client import call_claude, AIError


@shared_task
def ai_test_request(school_id, user_id):
    """Test AI request for a school."""
    try:
        school = School.objects.get(pk=school_id)
        user = User.objects.get(pk=user_id)

        call_claude(
            school=school,
            user=user,
            feature="test",
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=10,
        )
        pass
    except AIError:
        # Already logged by call_claude
        pass
    except Exception:
        # Unexpected errors - could log separately if needed
        pass
    pass
