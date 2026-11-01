"""Application-owned identity collection; no Engine namespace access."""
from .auth import UserExists

DATABASE = "telecom_identity"
COLLECTION = "users"


class MongoUserStore:
    def __init__(self, database):
        if database.name != DATABASE:
            raise ValueError("Use the designated application identity database")
        self.collection = database[COLLECTION]
        self.sessions = database["sessions"]
        self.attempts = database["login_attempts"]

    def provision(self):
        # Unique email already uses _id; UUID lookup remains uniquely constrained.
        self.collection.create_index("user_id", unique=True)
        self.sessions.create_index("expires_at", expireAfterSeconds=0)
        self.attempts.create_index("expires_at", expireAfterSeconds=0)

    def insert_session(self, session):
        self.sessions.insert_one(session)

    def get_session(self, digest, now):
        return self.sessions.find_one({"_id": digest, "expires_at": {"$gt": now}})

    def delete_session(self, digest):
        self.sessions.delete_one({"_id": digest})

    def consume_attempt(self, key, expires_at):
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError
        update = {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": expires_at}}
        try:
            result = self.attempts.find_one_and_update(
                {"_id": key}, update, upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            result = self.attempts.find_one_and_update(
                {"_id": key}, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
        return result["count"]

    def get(self, email):
        return self.collection.find_one({"_id": email})

    def insert(self, user):
        from pymongo.errors import DuplicateKeyError
        try:
            # _id is normalized email: MongoDB atomically enforces uniqueness.
            self.collection.insert_one(user)
        except DuplicateKeyError:
            raise UserExists("Email already registered") from None

    def update_profile(self, email, user_id, expected_revision, values):
        revision = ({"$or": [{"profile_revision": 0}, {"profile_revision": {"$exists": False}}]}
                    if expected_revision == 0 else {"profile_revision": expected_revision})
        result = self.collection.update_one(
            {"_id": email, "user_id": user_id, "active": True, **revision},
            {"$set": {f"profile.{key}": value for key, value in values.items()},
             "$inc": {"profile_revision": 1}},
        )
        return result.modified_count == 1

    def update_avatar(self, email, user_id, expected_revision, content):
        revision = ({"$or": [{"profile_revision": 0}, {"profile_revision": {"$exists": False}}]}
                    if expected_revision == 0 else {"profile_revision": expected_revision})
        changes = ({"$unset": {"profile.avatar": ""}} if content is None
                   else {"$set": {"profile.avatar": content}})
        return self.collection.update_one(
            {"_id": email, "user_id": user_id, "active": True, **revision},
            {**changes, "$inc": {"profile_revision": 1}},
        ).modified_count == 1

    def replace_password(self, email, user_id, expected_hash, replacement):
        return self.collection.update_one(
            {"_id": email, "user_id": user_id, "active": True, "password_hash": expected_hash},
            {"$set": {"password_hash": replacement}, "$inc": {"credential_version": 1}},
        ).modified_count == 1
