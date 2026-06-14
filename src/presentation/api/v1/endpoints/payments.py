"""Payments endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import PaymentCreateDTO
from application.use_cases import CreatePaymentUseCase, ListPaymentsUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import payment_dto_to_response
from presentation.api.v1.schemas.requests import PaymentCreateRequest
from presentation.api.v1.schemas.responses import PaymentResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/me", response_model=list[PaymentResponse])
@inject
async def list_my_payments(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListPaymentsUseCase],
) -> list[PaymentResponse]:
    user_id = resolve_user_id(credentials)
    payments = await use_case.execute(user_id)
    return [payment_dto_to_response(p) for p in payments]


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_payment(
    body: PaymentCreateRequest,
    use_case: FromDishka[CreatePaymentUseCase],
) -> PaymentResponse:
    dto = PaymentCreateDTO(
        user_id=body.user_id,
        plan_id=body.plan_id,
        amount=body.amount,
        status=body.status,
        robokassa_invoice_id=body.robokassa_invoice_id,
        idempotency_key=body.idempotency_key,
    )
    result = await use_case.execute(dto)
    return payment_dto_to_response(result)
