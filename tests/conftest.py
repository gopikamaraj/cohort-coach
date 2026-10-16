"""Shared pytest setup."""

from hypothesis import settings

# Property tests check logic, not speed: a loaded CI or laptop must not fail them on timing.
settings.register_profile("default", deadline=None)
settings.load_profile("default")
