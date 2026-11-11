from django.conf import settings
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.test import TestCase

PASSWORD = "correct horse battery staple"


class PasswordHashingTests(TestCase):
    """ADR-0001 claims Argon2id with parameters pinned in settings. Check it.

    These assertions exist because the claim is easy to break silently: a
    reordered PASSWORD_HASHERS or a fast test-only hasher would leave every
    other test passing while production hashing quietly changed.
    """

    def test_passwords_are_hashed_with_argon2id(self):
        encoded = make_password(PASSWORD)

        self.assertTrue(
            encoded.startswith("argon2$argon2id$"),
            f"expected an Argon2id hash, got {encoded.split('$')[0]!r}",
        )

    def test_cost_parameters_come_from_settings(self):
        hasher = identify_hasher(make_password(PASSWORD))

        self.assertEqual(hasher.time_cost, settings.ARGON2_TIME_COST)
        self.assertEqual(hasher.memory_cost, settings.ARGON2_MEMORY_COST)
        self.assertEqual(hasher.parallelism, settings.ARGON2_PARALLELISM)

    def test_verification_round_trips(self):
        encoded = make_password(PASSWORD)

        self.assertTrue(check_password(PASSWORD, encoded))
        self.assertFalse(check_password(PASSWORD + "x", encoded))

    def test_the_plaintext_does_not_appear_in_the_hash(self):
        self.assertNotIn(PASSWORD, make_password(PASSWORD))
