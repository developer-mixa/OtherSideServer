"""Application use case tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from tests.conftest import FakeEmailSender, FakeUnitOfWork, make_admin_user

from application.dtos import (
    CompanyGameCreateDTO,
    CompanyGameUpdateDTO,
    PaymentCreateDTO,
    PromocodeCreateDTO,
    PromocodeUpdateDTO,
    SubscriptionCreateDTO,
    SubscriptionPlanCreateDTO,
    SubscriptionPlanUpdateDTO,
    SubscriptionUpdateDTO,
    UserCreateDTO,
    UserUpdateDTO,
)
from application.use_cases import (
    CreateCompanyGameUseCase,
    CreatePaymentUseCase,
    CreatePromocodeUseCase,
    CreateRoleUseCase,
    CreateSubscriptionPlanUseCase,
    CreateSubscriptionUseCase,
    DeleteCompanyGameUseCase,
    DeletePromocodeUseCase,
    DeleteSubscriptionPlanUseCase,
    DeleteSubscriptionUseCase,
    GetCurrentUserUseCase,
    ListRolesUseCase,
    ListSubscriptionsUseCase,
    ListUsersUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
    ResendVerificationCodeUseCase,
    UpdateCompanyGameUseCase,
    UpdatePromocodeUseCase,
    UpdateSubscriptionPlanUseCase,
    UpdateSubscriptionUseCase,
    UpdateUserUseCase,
    VerifyEmailUseCase,
)
from config.security import hash_password, hash_verification_code
from domain.entities import CompanyGame, PromocodeEntity, Role, Subscription, SubscriptionPlan, User
from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EmailNotVerifiedError,
    EntityNotFoundError,
    RateLimitError,
    ValidationError,
)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def email_sender() -> FakeEmailSender:
    return FakeEmailSender()


class TestRegisterUserUseCase:
    async def test_register_success(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="newuser",
            email="new@example.com",
            password="password123",
            consent_personal_data=True,
        )
        result = await use_case.execute(dto)
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.is_admin is False
        assert result.is_verified is False

    async def test_register_sends_verification_code(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="codeuser",
            email="codeuser@example.com",
            password="password123",
            consent_personal_data=True,
        )
        await use_case.execute(dto)
        assert len(email_sender.sent) == 1
        to_email, code = email_sender.sent[0]
        assert to_email == "codeuser@example.com"
        assert len(code) == 6 and code.isdigit()
        stored_user = await uow.users.get_by_email("codeuser@example.com")
        assert stored_user is not None
        assert stored_user.verification_code_hash == hash_verification_code(code)

    async def test_register_always_assigns_user_role(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="plainuser",
            email="plain@example.com",
            password="password123",
            consent_personal_data=True,
        )
        result = await use_case.execute(dto)
        user_role = await uow.roles.get_by_name("user")
        assert user_role is not None
        assert result.role_id == user_role.id

    async def test_register_duplicate_verified_email(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        user = User.create("existing", "dup@example.com", "hash", is_verified=True)
        uow._store.users[user.id] = user
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="other",
            email="dup@example.com",
            password="password123",
            consent_personal_data=True,
        )
        with pytest.raises(DuplicateEntityError) as exc_info:
            await use_case.execute(dto)
        assert exc_info.value.code == "duplicate_user_email"

    async def test_register_reclaims_unverified_account(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        """A signup abandoned at the code-entry step must not lock the address forever."""
        stale = User.create("stale", "retry@example.com", "old-hash")
        stale.verification_code_hash = hash_verification_code("111111")
        stale.verification_attempts = 5
        uow._store.users[stale.id] = stale
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="retryuser",
            email="retry@example.com",
            password="password123",
            consent_personal_data=True,
        )
        result = await use_case.execute(dto)

        assert result.id == stale.id
        assert result.username == "retryuser"
        assert len(email_sender.sent) == 1
        _, code = email_sender.sent[0]
        stored = await uow.users.get_by_email("retry@example.com")
        assert stored is not None
        assert stored.verification_code_hash == hash_verification_code(code)
        assert stored.verification_attempts == 0
        assert stored.password_hash != "old-hash"
        assert stored.role_id is not None

    async def test_register_reclaim_is_throttled_within_cooldown(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        """Re-registering is a send path too, so it obeys the same cooldown."""
        stale = User.create("stale", "spam@example.com", "old-hash")
        stale.verification_code_sent_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        uow._store.users[stale.id] = stale
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="spamuser",
            email="spam@example.com",
            password="password123",
            consent_personal_data=True,
        )
        with pytest.raises(RateLimitError):
            await use_case.execute(dto)
        assert email_sender.sent == []

    async def test_register_rejects_username_owned_by_another_user(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        taken = User.create("taken", "someone@example.com", "hash", is_verified=True)
        uow._store.users[taken.id] = taken
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="taken",
            email="newcomer@example.com",
            password="password123",
            consent_personal_data=True,
        )
        with pytest.raises(DuplicateEntityError) as exc_info:
            await use_case.execute(dto)
        assert exc_info.value.code == "duplicate_user_username"

    async def test_register_requires_consent(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        use_case = RegisterUserUseCase(uow, email_sender)
        dto = UserCreateDTO(
            username="noconsent",
            email="noconsent@example.com",
            password="password123",
            consent_personal_data=False,
        )
        with pytest.raises(ValidationError):
            await use_case.execute(dto)


class TestLoginUserUseCase:
    async def test_login_success(self, uow: FakeUnitOfWork) -> None:
        user = User.create(
            "loginuser", "login@example.com", hash_password("password123"), is_verified=True
        )
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        result = await use_case.execute("login@example.com", "password123")
        assert result.access_token

    async def test_login_wrong_password(self, uow: FakeUnitOfWork) -> None:
        user = User.create(
            "loginuser", "login@example.com", hash_password("password123"), is_verified=True
        )
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        with pytest.raises(AuthenticationError):
            await use_case.execute("login@example.com", "wrongpass")

    async def test_login_blocked_user_rejected(self, uow: FakeUnitOfWork) -> None:
        user = User.create(
            "blockeduser",
            "blocked@example.com",
            hash_password("password123"),
            is_verified=True,
        )
        user.is_blocked = True
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        with pytest.raises(AuthorizationError):
            await use_case.execute("blocked@example.com", "password123")

    async def test_login_unverified_user_rejected(self, uow: FakeUnitOfWork) -> None:
        user = User.create("unverifieduser", "unverified@example.com", hash_password("password123"))
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        with pytest.raises(EmailNotVerifiedError):
            await use_case.execute("unverified@example.com", "password123")


class TestVerifyEmailUseCase:
    async def test_verify_email_success(self, uow: FakeUnitOfWork) -> None:
        user = User.create("pending", "pending@example.com", "hash")
        user.verification_code_hash = hash_verification_code("123456")
        user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        uow._store.users[user.id] = user

        use_case = VerifyEmailUseCase(uow)
        result = await use_case.execute("pending@example.com", "123456")
        assert result.is_verified is True
        stored_user = await uow.users.get_by_email("pending@example.com")
        assert stored_user is not None
        assert stored_user.verification_code_hash is None

    async def test_verify_email_wrong_code_increments_attempts(self, uow: FakeUnitOfWork) -> None:
        user = User.create("pending", "pending2@example.com", "hash")
        user.verification_code_hash = hash_verification_code("123456")
        user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        uow._store.users[user.id] = user

        use_case = VerifyEmailUseCase(uow)
        with pytest.raises(ValidationError):
            await use_case.execute("pending2@example.com", "000000")

        stored_user = await uow.users.get_by_email("pending2@example.com")
        assert stored_user is not None
        assert stored_user.verification_attempts == 1
        assert stored_user.is_verified is False

    async def test_verify_email_expired_code_rejected(self, uow: FakeUnitOfWork) -> None:
        user = User.create("pending", "expired@example.com", "hash")
        user.verification_code_hash = hash_verification_code("123456")
        user.verification_code_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        uow._store.users[user.id] = user

        use_case = VerifyEmailUseCase(uow)
        with pytest.raises(ValidationError):
            await use_case.execute("expired@example.com", "123456")

    async def test_verify_email_already_verified_rejected(self, uow: FakeUnitOfWork) -> None:
        user = User.create("verified", "verified@example.com", "hash", is_verified=True)
        uow._store.users[user.id] = user

        use_case = VerifyEmailUseCase(uow)
        with pytest.raises(ValidationError):
            await use_case.execute("verified@example.com", "123456")

    async def test_verify_email_unknown_user_not_found(self, uow: FakeUnitOfWork) -> None:
        use_case = VerifyEmailUseCase(uow)
        with pytest.raises(EntityNotFoundError):
            await use_case.execute("nobody@example.com", "123456")


class TestResendVerificationCodeUseCase:
    async def test_resend_is_throttled_within_cooldown(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        user = User.create("pending", "throttled@example.com", "hash")
        user.verification_code_sent_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        uow._store.users[user.id] = user

        use_case = ResendVerificationCodeUseCase(uow, email_sender)
        with pytest.raises(RateLimitError) as exc_info:
            await use_case.execute("throttled@example.com")

        assert exc_info.value.code == "verification_resend_too_soon"
        assert 0 < exc_info.value.retry_after_seconds <= 90
        assert email_sender.sent == []

    async def test_resend_allowed_once_cooldown_elapsed(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        user = User.create("pending", "cooled@example.com", "hash")
        user.verification_code_sent_at = datetime.now(timezone.utc) - timedelta(seconds=121)
        uow._store.users[user.id] = user

        use_case = ResendVerificationCodeUseCase(uow, email_sender)
        await use_case.execute("cooled@example.com")

        assert len(email_sender.sent) == 1
        stored_user = await uow.users.get_by_email("cooled@example.com")
        assert stored_user is not None
        assert stored_user.verification_code_sent_at is not None

    async def test_resend_sends_new_code(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        user = User.create("pending", "resend@example.com", "hash")
        user.verification_attempts = 3
        uow._store.users[user.id] = user

        use_case = ResendVerificationCodeUseCase(uow, email_sender)
        await use_case.execute("resend@example.com")

        assert len(email_sender.sent) == 1
        to_email, code = email_sender.sent[0]
        assert to_email == "resend@example.com"
        stored_user = await uow.users.get_by_email("resend@example.com")
        assert stored_user is not None
        assert stored_user.verification_attempts == 0
        assert stored_user.verification_code_hash == hash_verification_code(code)

    async def test_resend_already_verified_rejected(
        self, uow: FakeUnitOfWork, email_sender: FakeEmailSender
    ) -> None:
        user = User.create("verified", "verified2@example.com", "hash", is_verified=True)
        uow._store.users[user.id] = user

        use_case = ResendVerificationCodeUseCase(uow, email_sender)
        with pytest.raises(ValidationError):
            await use_case.execute("verified2@example.com")


class TestGetCurrentUserUseCase:
    async def test_get_existing_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("me", "me@example.com", "hash")
        uow._store.users[user.id] = user
        result = await GetCurrentUserUseCase(uow).execute(user.id)
        assert result.email == "me@example.com"

    async def test_get_missing_user(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(EntityNotFoundError):
            await GetCurrentUserUseCase(uow).execute(uuid4())


class TestListUsersUseCase:
    async def test_list_users_requires_admin(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("plain", "plain@example.com", "hash")
        uow._store.users[user.id] = user
        result = await ListUsersUseCase(uow).execute(admin.id)
        emails = {u.email for u in result}
        assert "plain@example.com" in emails
        assert "admin@example.com" in emails

    async def test_list_users_forbidden_for_regular_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("plain", "plain2@example.com", "hash")
        uow._store.users[user.id] = user
        with pytest.raises(AuthorizationError):
            await ListUsersUseCase(uow).execute(user.id)


class TestUpdateUserUseCase:
    async def test_update_user_fields(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("target", "target@example.com", "hash")
        uow._store.users[user.id] = user
        dto = UserUpdateDTO(username="renamed", is_verified=True)
        result = await UpdateUserUseCase(uow).execute(admin.id, user.id, dto)
        assert result.username == "renamed"
        assert result.is_verified is True

    async def test_block_user(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("target2", "target2@example.com", "hash")
        uow._store.users[user.id] = user
        dto = UserUpdateDTO(is_blocked=True)
        result = await UpdateUserUseCase(uow).execute(admin.id, user.id, dto)
        assert result.is_blocked is True
        assert uow._store.users[user.id].is_blocked is True

    async def test_update_missing_user(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await UpdateUserUseCase(uow).execute(admin.id, uuid4(), UserUpdateDTO(username="x"))

    async def test_update_user_forbidden_for_regular_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("plain3", "plain3@example.com", "hash")
        uow._store.users[user.id] = user
        with pytest.raises(AuthorizationError):
            await UpdateUserUseCase(uow).execute(user.id, user.id, UserUpdateDTO(username="x"))


class TestRoleUseCases:
    async def test_create_and_list_roles(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        created = await CreateRoleUseCase(uow).execute(admin.id, "moderator")
        roles = await ListRolesUseCase(uow).execute(admin.id)
        assert created.role == "moderator"
        assert any(role.role == "moderator" for role in roles)

    async def test_create_duplicate_role(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        uow._store.roles[uuid4()] = Role.create("custom-admin")
        with pytest.raises(DuplicateEntityError):
            await CreateRoleUseCase(uow).execute(admin.id, "custom-admin")

    async def test_list_roles_forbidden_for_regular_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("plain", "plain@example.com", "hash")
        uow._store.users[user.id] = user
        with pytest.raises(AuthorizationError):
            await ListRolesUseCase(uow).execute(user.id)


class TestCompanyGameUseCases:
    async def test_create_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        result = await CreateCompanyGameUseCase(uow).execute(
            admin.id, CompanyGameCreateDTO(game="CS2")
        )
        assert result.game == "CS2"

    async def test_delete_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        game = CompanyGame.create("Dota2")
        uow._store.company_games[game.id] = game
        await DeleteCompanyGameUseCase(uow).execute(admin.id, game.id)
        assert game.id not in uow._store.company_games

    async def test_delete_missing_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await DeleteCompanyGameUseCase(uow).execute(admin.id, uuid4())

    async def test_update_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        game = CompanyGame.create("OldName")
        uow._store.company_games[game.id] = game
        dto = CompanyGameUpdateDTO(game="NewName")
        result = await UpdateCompanyGameUseCase(uow).execute(admin.id, game.id, dto)
        assert result.game == "NewName"

    async def test_update_missing_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await UpdateCompanyGameUseCase(uow).execute(
                admin.id, uuid4(), CompanyGameUpdateDTO(game="X")
            )

    async def test_update_game_forbidden_for_regular_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("plain", "plain4@example.com", "hash")
        uow._store.users[user.id] = user
        game = CompanyGame.create("Game")
        uow._store.company_games[game.id] = game
        with pytest.raises(AuthorizationError):
            await UpdateCompanyGameUseCase(uow).execute(
                user.id, game.id, CompanyGameUpdateDTO(game="X")
            )


class TestSubscriptionPlanUseCases:
    async def test_create_plan_with_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        game = CompanyGame.create("Minecraft")
        uow._store.company_games[game.id] = game
        dto = SubscriptionPlanCreateDTO(type="monthly", game_id=game.id, duration_days=30)
        result = await CreateSubscriptionPlanUseCase(uow).execute(admin.id, dto)
        assert result.type == "monthly"
        assert result.duration_days == 30

    async def test_create_plan_missing_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        dto = SubscriptionPlanCreateDTO(type="monthly", game_id=uuid4())
        with pytest.raises(EntityNotFoundError):
            await CreateSubscriptionPlanUseCase(uow).execute(admin.id, dto)

    async def test_update_plan(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        dto = SubscriptionPlanUpdateDTO(type="yearly", is_active=False, duration_days=365)
        result = await UpdateSubscriptionPlanUseCase(uow).execute(admin.id, plan.id, dto)
        assert result.type == "yearly"
        assert result.is_active is False
        assert result.duration_days == 365

    async def test_update_missing_plan(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await UpdateSubscriptionPlanUseCase(uow).execute(
                admin.id, uuid4(), SubscriptionPlanUpdateDTO(type="yearly")
            )

    async def test_delete_plan(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        await DeleteSubscriptionPlanUseCase(uow).execute(admin.id, plan.id)
        assert plan.id not in uow._store.subscription_plans

    async def test_delete_missing_plan(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await DeleteSubscriptionPlanUseCase(uow).execute(admin.id, uuid4())


class TestSubscriptionUseCases:
    async def test_create_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("subuser", "sub@example.com", "hash")
        uow._store.users[user.id] = user
        dto = SubscriptionCreateDTO(user_id=user.id)
        result = await CreateSubscriptionUseCase(uow).execute(admin.id, dto)
        assert result.user_id == user.id

    async def test_list_own_subscriptions(self, uow: FakeUnitOfWork) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        uow._store.users[user.id] = user
        dto = SubscriptionCreateDTO(user_id=user.id)
        admin = make_admin_user(uow._store)
        await CreateSubscriptionUseCase(uow).execute(admin.id, dto)
        subs = await ListSubscriptionsUseCase(uow).execute(user.id)
        assert len(subs) == 1

    async def test_list_other_user_subscriptions_forbidden(self, uow: FakeUnitOfWork) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        other = User.create("other", "other@example.com", "hash")
        uow._store.users[user.id] = user
        uow._store.users[other.id] = other
        with pytest.raises(AuthorizationError):
            await ListSubscriptionsUseCase(uow).execute(user.id, other.id)

    async def test_update_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("subuser2", "sub2b@example.com", "hash")
        uow._store.users[user.id] = user
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        sub = Subscription.create(user_id=user.id)
        uow._store.subscriptions[sub.id] = sub
        dto = SubscriptionUpdateDTO(plan_id=plan.id)
        result = await UpdateSubscriptionUseCase(uow).execute(admin.id, sub.id, dto)
        assert result.plan_id == plan.id

    async def test_update_missing_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await UpdateSubscriptionUseCase(uow).execute(admin.id, uuid4(), SubscriptionUpdateDTO())

    async def test_delete_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("subuser3", "sub3@example.com", "hash")
        uow._store.users[user.id] = user
        sub = Subscription.create(user_id=user.id)
        uow._store.subscriptions[sub.id] = sub
        await DeleteSubscriptionUseCase(uow).execute(admin.id, sub.id)
        assert sub.id not in uow._store.subscriptions

    async def test_delete_missing_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await DeleteSubscriptionUseCase(uow).execute(admin.id, uuid4())


class TestPromocodeUseCases:
    async def test_create_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        dto = PromocodeCreateDTO(code="SAVE10", plan_id=plan.id)
        result = await CreatePromocodeUseCase(uow).execute(admin.id, dto)
        assert result.code == "SAVE10"

    async def test_update_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        code = PromocodeEntity.create("SAVE10", plan.id)
        uow._store.promocodes[code.id] = code
        dto = PromocodeUpdateDTO(code="save20", is_active=False)
        result = await UpdatePromocodeUseCase(uow).execute(admin.id, code.id, dto)
        assert result.code == "SAVE20"
        assert result.is_active is False

    async def test_update_missing_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await UpdatePromocodeUseCase(uow).execute(
                admin.id, uuid4(), PromocodeUpdateDTO(is_active=False)
            )

    async def test_delete_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        code = PromocodeEntity.create("DEL10", plan.id)
        uow._store.promocodes[code.id] = code
        await DeletePromocodeUseCase(uow).execute(admin.id, code.id)
        assert code.id not in uow._store.promocodes

    async def test_delete_missing_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await DeletePromocodeUseCase(uow).execute(admin.id, uuid4())


class TestPaymentUseCases:
    async def test_create_payment_idempotent(self, uow: FakeUnitOfWork) -> None:
        user = User.create("payuser", "pay@example.com", "hash")
        plan = SubscriptionPlan.create("monthly")
        uow._store.users[user.id] = user
        uow._store.subscription_plans[plan.id] = plan
        dto = PaymentCreateDTO(
            user_id=user.id,
            plan_id=plan.id,
            amount=Decimal("100.00"),
            status="pending",
            robokassa_invoice_id="inv-1",
            idempotency_key="idem-1",
        )
        first = await CreatePaymentUseCase(uow).execute(dto)
        second = await CreatePaymentUseCase(uow).execute(dto)
        assert first.id == second.id

    async def test_create_payment_rejects_non_pending_status(self, uow: FakeUnitOfWork) -> None:
        user = User.create("payuser2", "pay2@example.com", "hash")
        plan = SubscriptionPlan.create("monthly")
        uow._store.users[user.id] = user
        uow._store.subscription_plans[plan.id] = plan
        dto = PaymentCreateDTO(
            user_id=user.id,
            plan_id=plan.id,
            amount=Decimal("100.00"),
            status="paid",
            robokassa_invoice_id="inv-2",
            idempotency_key="idem-2",
        )
        with pytest.raises(ValidationError):
            await CreatePaymentUseCase(uow).execute(dto)
