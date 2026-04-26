"""AUTH-05 anchor: the Phase 1 custom-User commitment still holds.

These three tests prove the Phase 1 decision (``AUTH_USER_MODEL =
'accounts.User'`` committed in the same commit as ``accounts/migrations/
0001_initial.py``) survives Phase 2's expanded settings footprint. If any
future plan drifts ``USERNAME_FIELD``, drops ``accounts_user``, or
accidentally re-enables the stock ``auth_user`` table, these tests fail.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import ProgrammingError, connection


def test_user_model_uses_email_username_field():
    user_model = get_user_model()
    assert user_model.USERNAME_FIELD == "email"
    assert user_model._meta.get_field("email").unique is True


@pytest.mark.django_db
def test_accounts_user_table_exists():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM accounts_user LIMIT 0")


@pytest.mark.django_db
def test_stock_auth_user_table_does_not_exist():
    with connection.cursor() as cursor, pytest.raises(ProgrammingError):
        cursor.execute("SELECT 1 FROM auth_user LIMIT 0")
