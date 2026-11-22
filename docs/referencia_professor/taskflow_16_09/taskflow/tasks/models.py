from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskflow.ext.db import db

if TYPE_CHECKING:
    from taskflow.auth.models import User
    from taskflow.projects.models import Project


# === Task (tarefas) ===
class Task(db.Model):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(db.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text)
    status: Mapped[str] = mapped_column(db.String(30), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(db.String(20), nullable=False, default="medium")
    position: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime)


    # ------------------------------------------------------
    # PROJETO
    # ------------------------------------------------------
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks"
    )

    # ------------------------------------------------------
    # USUARIO
    # ------------------------------------------------------
    created_by: Mapped["User"] = relationship(
        "User",
        back_populates="tasks_created",
        foreign_keys=[created_by_id]
    )

    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="tasks_assigned",
        foreign_keys=[assigned_to_id]
    )


    # ------------------------------------------------------
    # LOG TAREFA
    # ------------------------------------------------------
    logs: Mapped[List["LogTask"]] = relationship(
        "LogTask",
        back_populates="task",
        cascade="all, delete-orphan"
    )


    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} "
            f"title='{self.title}' "
            f"status='{self.status}' "
            f"priority='{self.priority}'>"
        )


# === LogTask (auditoria tarefas) ===
class LogTask(db.Model):
    __tablename__ = "log_tasks"

    id_modify: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    new_value: Mapped[str] = mapped_column(db.String(255), nullable=False)
    old_value: Mapped[str] = mapped_column(db.String(255), nullable=False)
    rev: Mapped[int] = mapped_column(db.Integer, nullable=False)
    new_status: Mapped[str] = mapped_column(db.String(255), nullable=False)
    old_status: Mapped[str] = mapped_column(db.String(255), nullable=False)
    data_modify: Mapped[datetime] = mapped_column(db.DateTime, nullable=False)
    type: Mapped[str] = mapped_column(db.String(60), nullable=False)


    # ------------------------------------------------------
    # TAREFA
    # ------------------------------------------------------
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="logs"
    )

    # ------------------------------------------------------
    # USUARIO
    # ------------------------------------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="task_logs"
    )


    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<LogTask id_modify={self.id_modify} "
            f"task_id={self.task_id} "
            f"user_id={self.user_id} "
            f"rev={self.rev} "
            f"type='{self.type}'>"
        )