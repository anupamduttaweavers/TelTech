from enum import Enum

from sqlalchemy import Column, String, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.mixings import TimeTrackingMix, DeleteTrackingMix, UUIDMix
from app.models.associations import role_permissions


class ActionType(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    MANAGE = "MANAGE"


class Permission(Base, UUIDMix, TimeTrackingMix, DeleteTrackingMix):
    __tablename__ = "permissions"

    __table_args__ = (
        UniqueConstraint("action", "resource_id", name="uq_permission_action_resource"),
    )

    action = Column(SAEnum(ActionType, name="action_type_enum"), nullable=False)
    resource_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(String, nullable=True)

    resource = relationship(
        "Resource",
        back_populates="permissions",
        lazy="selectin",
    )

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )
