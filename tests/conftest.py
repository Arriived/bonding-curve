from hypothesis import settings

settings.register_profile("research", max_examples=100, derandomize=True, deadline=None)
settings.load_profile("research")
