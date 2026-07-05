import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

GoalCategory = Enum(
    "retirement",
    "education",
    "home",
    "travel",
    "wealth",
    "emergency",
    name="goal_category",
)

RiskProfile = Enum(
    "conservative",
    "balanced",
    "aggressive",
    name="risk_profile",
)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(GoalCategory, nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_contribution: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_profile: Mapped[str] = mapped_column(RiskProfile, nullable=False, default="balanced")
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Computed fields refreshed by the planning engine
    on_track: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="goals")  # type: ignore[name-defined]
    simulations: Mapped[list["Simulation"]] = relationship(  # type: ignore[name-defined]
        "Simulation", back_populates="goal", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Goal id={self.id} name={self.name}>"
