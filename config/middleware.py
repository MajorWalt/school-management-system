"""
Django middleware for school management system.

Includes:
- AutoLogoutMiddleware: Automatic logout after 10 minutes of inactivity
"""

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
import time


class AutoLogoutMiddleware(MiddlewareMixin):
    """
    Automatic logout after 10 minutes of inactivity.
    
    Tracks user activity (page views, form submissions, etc.).
    If no activity for 10 minutes, logs out on next request.
    """
    
    # Paths that don't count as activity (static files, etc.)
    EXEMPT_PATHS = ['/static/', '/media/', '/api/health/']
    
    def process_request(self, request):
      
        # Only check authenticated users
        if not request.user.is_authenticated:
            return None
        pass
        
        # Skip exempt paths
        if self._is_exempt_path(request.path):
            return None
        pass
        
        # Timeout is 30 minutes = 1800 seconds
        timeout_seconds = 30 * 60
        
        # Get last activity time from session
        last_activity = request.session.get('_last_activity', int(time.time()))
        current_time = int(time.time())
        elapsed = current_time - last_activity
        
        # If inactive for 10 minutes, logout
        if elapsed > timeout_seconds:
            logout(request)
            return redirect(reverse('accounts:login'))
        pass
        
        # Update last activity time
        request.session['_last_activity'] = int(time.time())
        request.session.modified = True
        
        return None
    pass
    
    def _is_exempt_path(self, path):
      
        for exempt in self.EXEMPT_PATHS:
            if path.startswith(exempt):
                return True
        pass
        
        return False
    pass