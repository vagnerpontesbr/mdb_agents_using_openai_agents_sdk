import copy
import secrets
import unittest

from compatibility.demo_auth.auth import AccessDenied, Auth, BOOTSTRAP_EMAIL, UserExists


class Store:
    def __init__(self):
        self.users = {}

    def get(self, email):
        return copy.deepcopy(self.users.get(email))

    def insert(self, user):
        if user["_id"] in self.users:
            raise UserExists()
        self.users[user["_id"]] = copy.deepcopy(user)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.auth = Auth(self.store)
        self.admin_password = secrets.token_urlsafe(16)
        self.user_password = secrets.token_urlsafe(16)
        self.admin = self.auth.bootstrap(self.admin_password)

    def register_user(self):
        return self.auth.register(BOOTSTRAP_EMAIL, self.admin_password,
                                  email="synthetic@example.test", password=self.user_password)

    def test_admin_registers_and_user_authenticates_without_hash_exposure(self):
        user = self.register_user()
        self.assertEqual(user.role, "user")
        self.assertEqual(self.auth.authenticate(" Synthetic@Example.Test ", self.user_password), user)
        self.assertNotIn("password_hash", vars(user))
        stored = self.store.users[user.email]["password_hash"]
        self.assertNotIn(self.user_password, stored)
        self.assertTrue(stored.startswith("pbkdf2_sha256$600000$"))

    def test_non_admin_and_wrong_password_cannot_register(self):
        user = self.register_user()
        before = copy.deepcopy(self.store.users)
        for email, password in ((user.email, self.user_password),
                                (BOOTSTRAP_EMAIL, self.user_password)):
            with self.assertRaises(AccessDenied):
                self.auth.register(email, password, email="other@example.test",
                                   password=secrets.token_urlsafe(16), role="admin")
        self.assertEqual(self.store.users, before)

    def test_bootstrap_and_case_duplicate_never_overwrite(self):
        before = copy.deepcopy(self.store.users)
        with self.assertRaises(UserExists):
            self.auth.bootstrap(self.user_password)
        with self.assertRaises(UserExists):
            self.auth.register(BOOTSTRAP_EMAIL, self.admin_password,
                               email=BOOTSTRAP_EMAIL.upper(), password=self.user_password)
        self.assertEqual(self.store.users, before)

    def test_requester_only_even_when_other_actor_is_admin(self):
        user = self.register_user()
        self.assertEqual(self.auth.authorize_requester(user.email, self.user_password,
                                                      requester_id=user.user_id), user)
        for email, password, requester in (
                (BOOTSTRAP_EMAIL, self.admin_password, user.user_id),
                (user.email, self.user_password, self.admin.user_id),
                (user.email, self.admin_password, user.user_id)):
            with self.assertRaises(AccessDenied):
                self.auth.authorize_requester(email, password, requester_id=requester)

    def test_invalid_and_disabled_identity_fail_closed(self):
        for email in ("missing@example.test", "invalid"):
            with self.assertRaisesRegex(AccessDenied, "Invalid credentials"):
                self.auth.authenticate(email, self.admin_password)
        self.store.users[BOOTSTRAP_EMAIL]["active"] = False
        with self.assertRaises(AccessDenied):
            self.auth.authenticate(BOOTSTRAP_EMAIL, self.admin_password)

    def test_only_two_roles_and_unique_salts(self):
        with self.assertRaises(ValueError):
            self.auth.register(BOOTSTRAP_EMAIL, self.admin_password,
                               email="synthetic@example.test", password=self.user_password,
                               role="owner")
        self.auth.register(BOOTSTRAP_EMAIL, self.admin_password, email="second@example.test",
                           password=self.admin_password, role="admin")
        self.assertNotEqual(self.store.users[BOOTSTRAP_EMAIL]["password_hash"],
                            self.store.users["second@example.test"]["password_hash"])


if __name__ == "__main__":
    unittest.main()
