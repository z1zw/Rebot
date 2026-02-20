"""UI template library."""

from __future__ import annotations


TEMPLATES = {
    "fitness": {
        "pages": ["Home", "Workout", "Programs", "Stats", "Profile"],
        "components": ["HeroCard", "ProgressRing", "WorkoutList", "CTAButton"],
        "style": "clean_health",
    },
    "health": {
        "pages": ["Overview", "Insights", "Plans", "Reminders", "Profile"],
        "components": ["VitalsCard", "ProgressChart", "ReminderList", "CTAButton"],
        "style": "calm_wellness",
    },
    "ecommerce": {
        "pages": ["Home", "Search", "Product", "Cart", "Profile"],
        "components": ["ProductGrid", "FilterBar", "CTAButton"],
        "style": "modern_commerce",
    },
    "finance": {
        "pages": ["Dashboard", "Accounts", "Insights", "Goals", "Profile"],
        "components": ["BalanceCard", "TrendChart", "GoalTracker", "CTAButton"],
        "style": "sharp_fintech",
    },
    "education": {
        "pages": ["Home", "Courses", "Lessons", "Progress", "Profile"],
        "components": ["CourseCard", "LessonList", "ProgressBar", "CTAButton"],
        "style": "bright_learning",
    },
    "travel": {
        "pages": ["Explore", "Trips", "Bookings", "Map", "Profile"],
        "components": ["DestinationCard", "MapPreview", "ItineraryList", "CTAButton"],
        "style": "adventure_travel",
    },
    "media": {
        "pages": ["Home", "Browse", "Player", "Library", "Profile"],
        "components": ["MediaRow", "HeroBanner", "CTAButton"],
        "style": "cinematic_media",
    },
    "enterprise": {
        "pages": ["Dashboard", "Workspaces", "Reports", "Automations", "Settings"],
        "components": ["KpiCard", "DataTable", "QuickAction", "CTAButton"],
        "style": "enterprise_grid",
    },
    "social": {
        "pages": ["Feed", "Messages", "Explore", "Profile"],
        "components": ["PostCard", "StoryRow", "CTAButton"],
        "style": "vibrant_social",
    },
    "tools": {
        "pages": ["Dashboard", "Tasks", "Insights", "Settings"],
        "components": ["DataCard", "QuickAction", "CTAButton"],
        "style": "clean_productivity",
    },
}
