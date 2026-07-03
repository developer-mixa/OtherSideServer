"""Contact form endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import ContactSubmissionCreateDTO
from application.use_cases.contact import ListContactSubmissionsUseCase, SubmitContactUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import contact_submission_dto_to_response
from presentation.api.v1.schemas.requests import ContactSubmitRequest
from presentation.api.v1.schemas.responses import ContactSubmissionResponse

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "/submissions",
    response_model=ContactSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def submit_contact(
    body: ContactSubmitRequest,
    use_case: FromDishka[SubmitContactUseCase],
) -> ContactSubmissionResponse:
    dto = ContactSubmissionCreateDTO(
        name=body.name,
        phone=body.phone,
        email=body.email,
        message=body.message,
        consent_personal_data=body.consent_personal_data,
        consent_privacy=body.consent_privacy,
    )
    result = await use_case.execute(dto)
    return contact_submission_dto_to_response(result)


@router.get("/submissions", response_model=list[ContactSubmissionResponse])
@inject
async def list_contact_submissions(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListContactSubmissionsUseCase],
) -> list[ContactSubmissionResponse]:
    user_id = resolve_user_id(credentials)
    results = await use_case.execute(user_id)
    return [contact_submission_dto_to_response(item) for item in results]
