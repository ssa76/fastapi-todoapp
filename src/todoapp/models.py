from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# SQLAlchemy 2.x typed mappings: `Mapped[T]` is NOT NULL, `Mapped[T | None]` is nullable.
# Column types are inferred from the annotation (str -> VARCHAR(255), int -> INTEGER, ...).


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str]


class Todos(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    priority: Mapped[int]
    complete: Mapped[bool] = mapped_column(default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
