"""Domain service tests."""

from datetime import date
from uuid import uuid4

from domain.entities import Subscription, SubscriptionPlan
from domain.services import SubscriptionService


class TestSubscriptionService:
    def test_calculate_active_until_monthly(self) -> None:
        plan = SubscriptionPlan.create("monthly")
        result = SubscriptionService.calculate_active_until(plan, date(2025, 1, 1))
        assert result == date(2025, 1, 31)

    def test_calculate_active_until_yearly(self) -> None:
        plan = SubscriptionPlan.create("yearly")
        result = SubscriptionService.calculate_active_until(plan, date(2025, 1, 1))
        assert result == date(2026, 1, 1)

    def test_extend_subscription(self) -> None:
        plan = SubscriptionPlan.create("monthly")
        sub = Subscription.create(user_id=uuid4(), active_until=date(2025, 6, 1))
        extended = SubscriptionService.extend_subscription(sub, plan, date(2025, 5, 1))
        assert extended.active_until == date(2025, 7, 2)

    def test_can_apply_promocode(self) -> None:
        plan_id = uuid4()
        assert SubscriptionService.can_apply_promocode(True, plan_id, plan_id) is True
        assert SubscriptionService.can_apply_promocode(False, plan_id, plan_id) is False
        assert SubscriptionService.can_apply_promocode(True, plan_id, uuid4()) is False
