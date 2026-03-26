from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.mixings import TimeTrackingMix, DeleteTrackingMix, UUIDMix
from app.models.associations import role_permissions


class Role(Base, UUIDMix, TimeTrackingMix, DeleteTrackingMix):
    __tablename__ = "roles"

    role_name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    users = relationship(
        "AdminUser",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )
