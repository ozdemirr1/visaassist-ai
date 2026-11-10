"""Read access to the active requirement set, shared by the checklist and application files."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def active_set_id(session: Session) -> str | None:
    return session.scalar(select(models.RequirementSet.id).where(models.RequirementSet.active))


def destinations(session: Session, set_id: str) -> set[str]:
    """Destinations that have a national layer in the set."""
    return set(
        session.scalars(
            select(models.Requirement.destination)
            .where(
                models.Requirement.requirement_set_id == set_id,
                models.Requirement.destination.is_not(None),
            )
            .distinct()
        )
    )
