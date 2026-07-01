"""API v1 router."""

from fastapi import APIRouter

from presentation.api.v1.endpoints import (
    auth,
    company_games,
    contact,
    landing,
    payments,
    promocodes,
    roles,
    settings,
    subscription_plans,
    subscriptions,
)

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(settings.router)
router.include_router(contact.router)
router.include_router(landing.router)
router.include_router(roles.router)
router.include_router(company_games.router)
router.include_router(subscription_plans.router)
router.include_router(subscriptions.router)
router.include_router(promocodes.router)
router.include_router(payments.router)
