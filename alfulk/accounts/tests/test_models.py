"""The user model and its manager: identity, defaults, and password storage."""

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django.test import TestCase

User = get_user_model()

PASSWORD = "correct horse battery staple"


class CreateUserTests(TestCase):
    def test_email_is_stored_as_entered_apart_from_trimming(self):
        user = User.objects.create_user(
            email="  Ada@Example.com ", display_name="Ada", password=PASSWORD
        )

        self.assertEqual(user.email, "Ada@example.com")

    def test_display_name_is_trimmed(self):
        user = User.objects.create_user(
            email="ada@example.com", display_name="  Ada Lovelace  ", password=PASSWORD
        )

        self.assertEqual(user.display_name, "Ada Lovelace")

    def test_defaults(self):
        user = User.objects.create_user(
            email="ada@example.com", display_name="Ada", password=PASSWORD
        )

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.created_at)
        self.assertIsNone(user.last_login)

    def test_email_is_required(self):
        for missing in ("", "   ", None):
            with self.subTest(email=missing), self.assertRaises(ValueError):
                User.objects.create_user(email=missing, display_name="Ada", password=PASSWORD)

    def test_display_name_is_required(self):
        for missing in ("", "   ", None):
            with self.subTest(display_name=missing), self.assertRaises(ValueError):
                User.objects.create_user(
                    email="ada@example.com", display_name=missing, password=PASSWORD
                )

    def test_str_and_name_helpers(self):
        user = User.objects.create_user(
            email="ada@example.com", display_name="Ada", password=PASSWORD
        )

        self.assertEqual(str(user), "ada@example.com")
        self.assertEqual(user.get_full_name(), "Ada")
        self.assertEqual(user.get_short_name(), "Ada")


class PasswordStorageTests(TestCase):
    """AC-SU-7."""

    def test_password_is_stored_as_an_argon2id_hash(self):
        user = User.objects.create_user(
            email="ada@example.com", display_name="Ada", password=PASSWORD
        )

        self.assertTrue(user.password.startswith("argon2$argon2id$"))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password("something else entirely"))

    def test_no_plaintext_password_reaches_the_database(self):
        User.objects.create_user(email="ada@example.com", display_name="Ada", password=PASSWORD)

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {User._meta.db_table}")  # noqa: S608
            rows = cursor.fetchall()

        stored = " ".join(str(value) for row in rows for value in row)
        self.assertNotIn(PASSWORD, stored)

    def test_an_omitted_password_is_unusable_rather_than_empty(self):
        user = User.objects.create_user(email="ada@example.com", display_name="Ada")

        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.check_password(""))


class CreateSuperuserTests(TestCase):
    def test_sets_both_flags(self):
        user = User.objects.create_superuser(
            email="root@example.com", display_name="Root", password=PASSWORD
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_rejects_a_superuser_that_is_not_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root@example.com",
                display_name="Root",
                password=PASSWORD,
                is_staff=False,
            )

    def test_rejects_a_superuser_without_the_superuser_flag(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="root@example.com",
                display_name="Root",
                password=PASSWORD,
                is_superuser=False,
            )


class LookupByEmailTests(TestCase):
    """AC-SU-4: letter case and surrounding whitespace are not part of identity."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="Ada@Example.com", display_name="Ada", password=PASSWORD
        )

    def test_get_by_natural_key_ignores_case_and_surrounding_whitespace(self):
        for variant in (
            "Ada@Example.com",
            "ada@example.com",
            "ADA@EXAMPLE.COM",
            "  ada@example.com  ",
        ):
            with self.subTest(email=variant):
                self.assertEqual(User.objects.get_by_natural_key(variant), self.user)

    def test_get_by_natural_key_still_distinguishes_different_addresses(self):
        with self.assertRaises(User.DoesNotExist):
            User.objects.get_by_natural_key("grace@example.com")

    def test_authenticate_accepts_a_case_variant_of_the_email(self):
        self.assertEqual(authenticate(username="  ADA@example.COM ", password=PASSWORD), self.user)

    def test_authenticate_rejects_the_wrong_password(self):
        self.assertIsNone(authenticate(username="ada@example.com", password="wrong"))
