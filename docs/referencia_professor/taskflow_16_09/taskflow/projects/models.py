from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskflow.ext.db import db

if TYPE_CHECKING:
    from taskflow.auth.models import User
    from taskflow.tasks.models import Task

# === Project (projetos) ===
class Project(db.Model):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_project_organization_slug"
        ),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(150), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text)
    is_private: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())


    # ------------------------------------------------------
    # ORGANIZACAO
    # ------------------------------------------------------
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects"
    )

    # ------------------------------------------------------
    # USUARIOS
    # ------------------------------------------------------    
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="projects_owned",
        foreign_keys=[owner_id]
    )

    # ------------------------------------------------------
    # MEMBROS PROJETO
    # ------------------------------------------------------
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------
    # TAREFAS
    # ------------------------------------------------------
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan"
    )


    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<Project id={self.id} "
            f"name='{self.name}' "
            f"slug='{self.slug}'>"
        )


# === Project Member (membros projetos) ===
class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member_project_user"
        ),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(db.String(30), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now())


    # ------------------------------------------------------
    # PROJETO
    # ------------------------------------------------------
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="members"
    )

    # ------------------------------------------------------
    # USUARIO
    # ------------------------------------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="project_memberships"
    )

    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<ProjectMember id={self.id} "
            f"project_id={self.project_id} "
            f"user_id={self.user_id} "
            f"role='{self.role}'>"
        )


# === Organization (Organizacao) ===
class Organization(db.Model):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(150), nullable=False)
    slug: Mapped[str] = mapped_column(db.String(150), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(db.Text)
    owner_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at: Mapped[datetime] = mapped_column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())


    # ------------------------------------------------------
    # USUARIO
    # ------------------------------------------------------
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="organizations_owned",
        foreign_keys=[owner_id]
    )

    # ------------------------------------------------------
    # PROJETO
    # ------------------------------------------------------
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    # ======================================================
    # REPRESENTACAO
    # ======================================================
    def __repr__(self) -> str:
        return (
            f"<Organization id={self.id} "
            f"name='{self.name}' "
            f"slug='{self.slug}'>"
        )