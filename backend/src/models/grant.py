from sqlalchemy import String, Double, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Grant(Base):
    __tablename__ = 'grants'
    __table_args__ = (UniqueConstraint('user_id', 'team', name='uq_grants_user_team'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    team: Mapped[str] = mapped_column(String(40))
    granted_by: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[float] = mapped_column(Double)
