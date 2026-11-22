from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskflow.ext.db import db

if TYPE_CHECKING:
    from taskflow.projects.models import Project, ProjectMember, Organization
    from taskflow.tasks.models import Task, LogTask


# === User (usuario) ===
class User(db.Model):
    __tablename__ = "users"

    # ======================================================
    # IDENTIFICACAO
    # ======================================================
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)

    # ======================================================
    # DADOS PRINCIPAIS
    # ======================================================
    username: Mapped[str] = mapped_column(db.String(50), nullable=False, index=True)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True, index=True)

    # ======================================================
    # PERFIL
    # ======================================================
    full_name: Mapped[str] = mapped_column(db.String(150), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(db.String(500))

    # ======================================================
    # SENHA LOCAL
    # ======================================================
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)

    # ======================================================
    # AUDITORIA USUARIO
    # ======================================================
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    create_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())


    # ------------------------------------------------------
    # PROJETOS
    # ------------------------------------------------------
    projects_owned: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="Project.owner_id"
    )

    # ------------------------------------------------------
    # MEMBROS DO PROJETO
    # ------------------------------------------------------
    project_memberships: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------
    # ORGANIZACAO
    # ------------------------------------------------------
    organizations_owned: Mapped[List["Organization"]] = relationship(
        "Organization",
        back_populates="owner",
        foreign_keys="Organization.owner_id"
    )

    # ------------------------------------------------------
    # TAREFAS
    # ------------------------------------------------------
    tasks_created: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="created_by",
        foreign_keys="Task.created_by_id"
    )

    tasks_assigned: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="assigned_to",
        foreign_keys="Task.assigned_to_id"
    )

    # ------------------------------------------------------
    # LOG DE TAREFAS
    # ------------------------------------------------------
    task_logs: Mapped[List["LogTask"]] = relationship(
        "LogTask",
        back_populates="user",
        foreign_keys="LogTask.user_id"
    )

    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<User id={self.id} "
            f"username='{self.username}' "
            f"email='{self.email}'>"
        )