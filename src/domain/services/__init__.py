"""Domain services — business logic that spans multiple entities."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from domain.entities import Subscription, SubscriptionPlan


class SubscriptionService:
    """Domain service for subscription lifecycle rules."""

    @staticmethod
    def calculate_active_until(plan: SubscriptionPlan, from_date: date | None = None) -> date:
        """Calculate subscription end date based on plan type."""
        start = from_date or date.today()
        plan_days = {
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365,
        }
        days = plan_days.get(plan.type.lower(), 30)
        return start + timedelta(days=days)

    @staticmethod
    def extend_subscription(
        subscription: Subscription,
        plan: SubscriptionPlan,
        from_date: date | None = None,
    ) -> Subscription:
        """Extend or create subscription period."""
        start = from_date or date.today()
        if subscription.active_until and subscription.active_until >= start:
            start = subscription.active_until + timedelta(days=1)
        subscription.active_until = SubscriptionService.calculate_active_until(plan, start)
        return subscription

    @staticmethod
    def can_apply_promocode(
        promocode_active: bool,
        plan_id: UUID,
        target_plan_id: UUID,
    ) -> bool:
        return promocode_active and plan_id == target_plan_id
