"""Payments endpoints."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import PaymentInitDTO
from application.use_cases import (
    GetPaymentUseCase,
    InitiatePaymentUseCase,
    ListPaymentsUseCase,
    ProcessRobokassaWebhookUseCase,
)
from config.deps import bearer_scheme, resolve_user_id
from domain.exceptions import EntityNotFoundError, PaymentVerificationError, ValidationError
from presentation.api.v1.mappers import payment_dto_to_response
from presentation.api.v1.schemas.requests import PaymentInitRequest
from presentation.api.v1.schemas.responses import PaymentInitResponse, PaymentResponse

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


@router.post("/init", response_model=PaymentInitResponse, status_code=status.HTTP_201_CREATED)
@inject
async def initiate_payment(
    body: PaymentInitRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[InitiatePaymentUseCase],
) -> PaymentInitResponse:
    user_id = resolve_user_id(credentials)
    result = await use_case.execute(
        user_id,
        PaymentInitDTO(plan_id=body.plan_id, idempotency_key=body.idempotency_key),
    )
    return PaymentInitResponse(
        payment_id=result.payment_id,
        payment_url=result.payment_url,
        robokassa_invoice_id=result.robokassa_invoice_id,
        amount=result.amount,
        status=result.status,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
@inject
async def get_payment(
    payment_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[GetPaymentUseCase],
) -> PaymentResponse:
    user_id = resolve_user_id(credentials)
    payment = await use_case.execute(user_id, payment_id)
    return payment_dto_to_response(payment)


@router.post("/robokassa/result")
@inject
async def robokassa_result(
    request: Request,
    use_case: FromDishka[ProcessRobokassaWebhookUseCase],
) -> Response:
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    try:
        body = await use_case.execute(payload)
        return Response(content=body, media_type="text/plain")
    except (PaymentVerificationError, EntityNotFoundError, ValidationError) as exc:
        return Response(content=exc.message, status_code=status.HTTP_400_BAD_REQUEST, media_type="text/plain")
