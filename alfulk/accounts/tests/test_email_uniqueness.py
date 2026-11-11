"""AC-SU-4: one account per email address, whatever the letter case.

Uniqueness has to hold in the database, because that is the only layer both
sign-ups go through when they arrive at the same moment. These tests therefore
reach past the manager: they prove the constraint rejects the second row even
when nothing in Python looked first.
"""

import threading

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase

User = get_user_model()

PASSWORD = "correct horse battery staple"


class CaseInsensitiveUniquenessTests(TestCase):
    def setUp(self):
        self.existing = User.objects.create_user(
            email="ada@example.com", display_name="Ada", password=PASSWORD
        )

    def test_the_database_rejects_a_case_variant(self):
        for variant in ("Ada@example.com", "ADA@EXAMPLE.COM", "  ADA@example.com  "):
            with self.subTest(email=variant):
                with self.assertRaises(IntegrityError) as caught, transaction.atomic():
                    User.objects.create_user(
                        email=variant, display_name="Impostor", password=PASSWORD
                    )

                self.assertIn("user_email_ci_unique", str(caught.exception))

        self.assertEqual(User.objects.count(), 1)

    def test_saving_the_model_directly_cannot_bypass_the_constraint(self):
        # No manager, no normalization, no pre-flight lookup: whatever the
        # application forgets to check, the index still holds.
        impostor = User(email="ADA@Example.com", display_name="Impostor")
        impostor.set_password(PASSWORD)

        with self.assertRaises(IntegrityError), transaction.atomic():
            impostor.save()

    def test_different_addresses_are_still_allowed(self):
        other = User.objects.create_user(
            email="grace@example.com", display_name="Grace", password=PASSWORD
        )

        self.assertNotEqual(other.pk, self.existing.pk)
        self.assertEqual(User.objects.count(), 2)


class ConcurrentSignUpTests(TransactionTestCase):
    """Two sign-ups for the same address at the same moment: exactly one wins.

    A `filter(email__iexact=...)` check before the insert passes in both
    transactions here -- neither can see the other's uncommitted row -- so this
    is the case that distinguishes a real constraint from a hopeful one.
    """

    def test_simultaneous_case_variant_sign_ups_cannot_both_commit(self):
        emails = ["race@example.com", "RACE@Example.com"]
        both_ready = threading.Barrier(len(emails), timeout=30)
        rejections = []

        def sign_up(email):
            # Hash outside the timed section so the two transactions overlap on
            # the insert rather than on Argon2.
            user = User(email=email, display_name="Racer")
            user.set_password(PASSWORD)
            try:
                both_ready.wait()
                with transaction.atomic():
                    user.save()
            except IntegrityError as exc:
                rejections.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=sign_up, args=(email,)) for email in emails]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        self.assertEqual(len(rejections), 1, "exactly one sign-up should be rejected")
        self.assertIn("user_email_ci_unique", str(rejections[0]))
        self.assertEqual(User.objects.count(), 1)
