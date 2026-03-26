from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

class TimeTrackingMix:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DeleteTrackingMix:
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        self.deleted_at = datetime.now(timezone.utc)

class UUIDMix:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)