def branding(request):
    profile = getattr(request, "school_profile", None)
    return {
        "primary_color":      getattr(profile, "primary_color",      "#1e40af"),
        "accent_color":       getattr(profile, "accent_color",        "#f59e0b"),
        "primary_text_color": getattr(profile, "primary_text_color",  "#ffffff"),
        "school_logo":        getattr(profile, "logo",                None),
        "school_tagline":     getattr(profile, "tagline",             ""),
    }