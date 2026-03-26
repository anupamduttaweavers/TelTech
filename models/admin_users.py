from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import relationship
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.models.base import Base
from app.models.mixings import TimeTrackingMix, DeleteTrackingMix, UUIDMix

ph = PasswordHasher()


class AdminUser(Base, TimeTrackingMix, DeleteTrackingMix, UUIDMix):
    __tablename__ = "admin_users"

    email = Column(CITEXT, nullable=False, unique=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)

    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    full_name = Column(String, index=True)

    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )

    def set_password(self, password: str):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False
