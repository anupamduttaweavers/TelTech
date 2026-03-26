from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.mixings import TimeTrackingMix, DeleteTrackingMix, UUIDMix


class Resource(Base, UUIDMix, TimeTrackingMix, DeleteTrackingMix):
    __tablename__ = "resources"

    resource_name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    permissions = relationship(
        "Permission",
        back_populates="resource",
        lazy="selectin",
    )
