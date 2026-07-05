import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Simulation inputs (snapshot at run time)
    num_simulations: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_contribution: Mapped[float] = mapped_column(Float, nullable=False)
    years_to_goal: Mapped[float] = mapped_column(Float, nullable=False)
    risk_profile: Mapped[str] = mapped_column(String(50), nullable=False)

    # Results
    success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    p10: Mapped[float] = mapped_column(Float, nullable=False)
    p25: Mapped[float] = mapped_column(Float, nullable=False)
    p50: Mapped[float] = mapped_column(Float, nullable=False)
    p75: Mapped[float] = mapped_column(Float, nullable=False)
    p90: Mapped[float] = mapped_column(Float, nullable=False)
    distribution: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="simulations")  # type: ignore[name-defined]
    goal: Mapped["Goal | None"] = relationship("Goal", back_populates="simulations")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Simulation id={self.id} success_rate={self.success_rate:.1f}%>"
