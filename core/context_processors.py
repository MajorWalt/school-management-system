def tenant(request):
    return {
        "school":         getattr(request, "school", None),
        "school_profile": getattr(request, "school_profile", None),
    }