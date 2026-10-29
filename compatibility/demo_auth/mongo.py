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
