"""Password hashing configured from settings rather than library defaults."""

from django.conf import settings
from django.contrib.auth.hashers import Argon2PasswordHasher


class AlfulkArgon2PasswordHasher(Argon2PasswordHasher):
    """Argon2id with cost parameters pinned in settings.

    Django's stock hasher hard-codes its cost parameters as class attributes,
    which means they change when Django or argon2-cffi changes them. Reading
    them from settings makes a tuning change an explicit, reviewable diff, and
    lets the test suite exercise the real hasher at cheap parameters instead of
    substituting a fast one that production never runs (ADR-0001).

    Because the parameters are part of the stored hash, Django's
    ``must_update`` re-hashes a user's password on their next successful
    sign-in whenever these values are raised.
    """

    time_cost = settings.ARGON2_TIME_COST
    memory_cost = settings.ARGON2_MEMORY_COST
    parallelism = settings.ARGON2_PARALLELISM
