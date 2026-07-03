"""Contact form use cases."""

from __future__ import annotations

from uuid import UUID

from application.auth import require_admin
from application.dtos import ContactSubmissionCreateDTO, ContactSubmissionDTO
from application.interfaces import UnitOfWorkProtocol
from application.mappers import contact_submission_to_dto
from domain.entities import ContactSubmission
from domain.exceptions import ValidationError


class SubmitContactUseCase:
    """Persist a public contact form submission."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: ContactSubmissionCreateDTO) -> ContactSubmissionDTO:
        if not dto.consent_personal_data or not dto.consent_privacy:
            raise ValidationError("Both consent checkboxes must be accepted")

        async with self._uow:
            entity = ContactSubmission.create(
                name=dto.name.strip(),
                phone=dto.phone.strip(),
                email=dto.email.strip().lower(),
                message=dto.message.strip() if dto.message else None,
                consent_personal_data=dto.consent_personal_data,
                consent_privacy=dto.consent_privacy,
            )
            await self._uow.contact_submissions.add(entity)
            await self._uow.commit()
            return contact_submission_to_dto(entity)


class ListContactSubmissionsUseCase:
    """List all contact submissions (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> list[ContactSubmissionDTO]:
        async with self._uow:
            await require_admin(self._uow, user_id)
            submissions = await self._uow.contact_submissions.list_all()
            return [contact_submission_to_dto(item) for item in submissions]
