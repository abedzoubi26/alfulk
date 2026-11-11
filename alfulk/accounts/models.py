"""The account identity: an email address, a display name, and a password hash.

Alfulk identifies people by email, so this model replaces Django's username
with one. It ships before anything else in increment 1 because Django resolves
``AUTH_USER_MODEL`` while building migrations: a table that references ``auth``
first, and a custom user second, is a data migration across the most sensitive
table we have.

Criteria referenced here live in ``docs/product/increment-1.md``.
"""

from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Value
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    """Creates accounts keyed on email, since there is no username to fall back on."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        """Trim surrounding whitespace before Django's own domain lowercasing.

        Trimming is part of identity, not cosmetics: ``" ada@example.com"`` and
        ``"ada@example.com"`` are the same person, so the spaces must not reach
        the column the uniqueness constraint reads. Letter case in the local
        part is preserved -- the address is stored as entered and the
        constraint, not the column, decides who is who.

        ``str()`` rather than a bare ``.strip()``: a non-string reaching here
        through ``authenticate()`` would otherwise raise ``AttributeError``,
        which ``ModelBackend`` does not catch, where stock Django coerces
        through the field and returns ``DoesNotExist``.
        """
        return super().normalize_email(str(email or "").strip())

    def get_by_natural_key(self, username):
        """Look an account up by email, ignoring letter case and surrounding space.

        ``Lower()`` on both sides rather than ``__iexact``: ``iexact`` compiles
        to ``UPPER(email) = UPPER(%s)``, which cannot use the unique index on
        ``LOWER(email)`` and which could disagree with the constraint that
        governs identity. Letting the database lower both operands keeps the
        lookup and the constraint on exactly one definition of sameness.
        """
        return self.annotate(email_key=Lower("email")).get(
            email_key=Lower(Value(self.normalize_email(username)))
        )

    def _create_user(self, email, display_name, password, **extra_fields):
        email = self.normalize_email(email)
        if not email:
            raise ValueError("An account needs an email address.")

        display_name = (display_name or "").strip()
        if not display_name:
            raise ValueError("An account needs a display name.")

        user = self.model(email=email, display_name=display_name, **extra_fields)
        # Never stores the plaintext, and an absent password becomes an
        # unusable hash rather than an empty one (AC-SU-7).
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, display_name, password, **extra_fields)

    def create_superuser(self, email, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self._create_user(email, display_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """A single person's account.

    ``last_login`` and ``password`` come from ``AbstractBaseUser``; the
    permission flags and relations from ``PermissionsMixin``.

    Inserting a user is how a duplicate address is detected, because the
    constraint below is the only layer that can decide it. Two requirements
    come with that, and both are easy to miss:

    * Wrap the insert in its own ``transaction.atomic()`` savepoint.
      ``ATOMIC_REQUESTS`` is on, so without a savepoint the failed insert
      poisons the request-wide transaction: the ``except`` block catches the
      ``IntegrityError``, then the next query -- re-rendering the form, or
      merely writing the session -- raises ``TransactionManagementError`` and
      the duplicate sign-up becomes a 500.
    * Discriminate on which constraint fired rather than catching
      ``IntegrityError`` bare, or a future foreign-key violation will tell
      someone their email address is taken::

          except IntegrityError as exc:
              diag = getattr(exc.__cause__, "diag", None)
              if diag and diag.constraint_name == "user_email_ci_unique":
                  ...  # the address already has an account
              raise
    """

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["display_name"]

    email = models.EmailField(
        "email address",
        max_length=254,
        help_text="Stored as entered; matched without regard to letter case.",
    )
    display_name = models.CharField("display name", max_length=80)
    is_active = models.BooleanField("active", default=True)
    is_staff = models.BooleanField("staff status", default=False)
    created_at = models.DateTimeField("created", auto_now_add=True)

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # The database is the only place this can be enforced. A form
            # check, a `clean()`, or a `filter(email__iexact=...)` before the
            # insert all lose the race between two simultaneous sign-ups
            # (AC-SU-4); callers handle IntegrityError as the duplicate case.
            models.UniqueConstraint(Lower("email"), name="user_email_ci_unique"),
        ]

    def save(self, *args, **kwargs):
        """Normalize the address on every write, not just the manager's.

        The constraint lowers but cannot trim, and widening it is the wrong
        fix: Postgres ``btrim`` strips spaces only, so ``Lower(Trim(email))``
        would still disagree with Python's ``.strip()`` about a tab or a
        newline -- two definitions of sameness again, which is what
        ``get_by_natural_key`` exists to avoid. Normalizing on write keeps one
        definition and leaves the index simple, so a caller that bypasses the
        manager cannot open ``" ada@example.com"`` as a second account.
        """
        if self.email is not None:
            self.email = UserManager.normalize_email(self.email)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name
