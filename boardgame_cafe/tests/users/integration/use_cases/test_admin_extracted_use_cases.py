from datetime import datetime, timedelta, timezone

import pytest

from features.users.application.query_services.admin_reports_query_service import (
    AdminReportsQueryService,
)
from features.users.application.use_cases.admin_catalogue_use_cases import (
    CatalogueManagementUseCase,
    ConflictError,
)
from features.users.application.use_cases.admin_content_use_cases import (
    ContentManagementUseCase,
)
from features.users.application.use_cases.admin_pricing_use_cases import (
    PricingManagementUseCase,
    UpdateBaseFeeCommand,
    UpdatePriceCommand,
)
from features.users.application.use_cases.admin_user_admin_use_cases import (
    SuspensionPolicyConflictError,
    UserAdminActionsUseCase,
)
from features.users.infrastructure import UserDB, hash_password
from features.users.infrastructure.adapters.admin_catalogue_adapter import (
    SqlAlchemyAdminCatalogueAdapter,
)
from features.users.infrastructure.adapters.admin_content_adapter import (
    SqlAlchemyAdminContentAdapter,
)
from features.users.infrastructure.adapters.admin_pricing_adapter import (
    SqlAlchemyAdminPricingAdapter,
)
from features.users.infrastructure.adapters.admin_reports_adapter import (
    SqlAlchemyAdminReportsAdapter,
)
from features.users.infrastructure.repositories import SqlAlchemyUserRepository
from shared.infrastructure import db



def _seed_user(*, role: str, name: str, email: str, is_suspended: bool = False) -> int:
    user = UserDB(
        role=role,
        name=name,
        email=email,
        password_hash=hash_password("AdminPass123"),
        is_suspended=is_suspended,
    )
    db.session.add(user)
    db.session.commit()
    return int(user.id)



def test_pricing_use_case_rejects_expired_timestamp_and_missing_table(app):
    use_case = PricingManagementUseCase(port=SqlAlchemyAdminPricingAdapter())

    with app.app_context():
        with pytest.raises(ValueError, match="must be in the future"):
            use_case.update_base_fee(
                UpdateBaseFeeCommand(
                    booking_base_fee_cents=2500,
                    booking_base_fee_active_until=(
                        datetime.now(timezone.utc) - timedelta(minutes=5)
                    ).isoformat(),
                )
            )

        with pytest.raises(LookupError, match="Table not found"):
            use_case.update_table_price(999999, UpdatePriceCommand(price_cents=12000))



def test_content_use_case_applies_cta_and_publish_state_rules(app):
    use_case = ContentManagementUseCase(port=SqlAlchemyAdminContentAdapter())

    with app.app_context():
        with pytest.raises(ValueError, match="cta_label and cta_url"):
            use_case.create_announcement(
                {
                    "title": "CTA mismatch",
                    "body": "Missing URL",
                    "cta_label": "Book now",
                },
                creator_id=None,
            )

        with pytest.raises(ValueError, match="title is required"):
            use_case.create_announcement(
                {"title": "   ", "body": "Body"},
                creator_id=None,
            )

        created = use_case.create_announcement(
            {"title": "Draft", "body": "Not published", "publish_now": False},
            creator_id=None,
        )

        with pytest.raises(ValueError, match="already unpublished"):
            use_case.unpublish_announcement(int(created["id"]))



def test_user_admin_actions_use_case_enforces_policy_and_role_filter(app):
    with app.app_context():
        active_admin_id = _seed_user(
            role="admin",
            name="Active Admin",
            email="active-admin-use-case@example.com",
            is_suspended=False,
        )
        acting_admin_id = _seed_user(
            role="admin",
            name="Suspended Admin",
            email="suspended-admin-use-case@example.com",
            is_suspended=True,
        )

        use_case = UserAdminActionsUseCase(user_repo=SqlAlchemyUserRepository())

        with pytest.raises(ValueError, match="Invalid role filter"):
            use_case.list_users("superadmin", None, acting_admin_id)

        with pytest.raises(SuspensionPolicyConflictError, match="last active admin"):
            use_case.set_suspension(active_admin_id, True, acting_admin_id)



def test_reports_query_service_handles_malformed_days_and_empty_data(app):
    query_service = AdminReportsQueryService(port=SqlAlchemyAdminReportsAdapter())

    with app.app_context():
        assert query_service.normalize_days("not-a-number") == 30
        assert query_service.normalize_days("0") == 1

        revenue = query_service.revenue_report(5)
        assert len(revenue) == 5
        assert all(item["total_cents"] == 0 for item in revenue)

        top_games = query_service.top_games_report(7)
        assert top_games["by_rating"] == []
        assert top_games["by_bookings"] == []



def test_catalogue_use_case_conflicts_and_missing_entities(app):
    use_case = CatalogueManagementUseCase(port=SqlAlchemyAdminCatalogueAdapter())

    with app.app_context():
        game = use_case.create_game(
            {
                "title": "Root",
                "min_players": 2,
                "max_players": 4,
                "playtime_min": 90,
                "complexity": 3.2,
                "price_cents": 4500,
            }
        )
        game_id = int(game["id"])

        use_case.create_copy(
            {
                "game_id": game_id,
                "copy_code": "ROOT-001",
                "status": "available",
            }
        )

        with pytest.raises(ConflictError, match="copy_code already exists"):
            use_case.create_copy(
                {
                    "game_id": game_id,
                    "copy_code": "ROOT-001",
                    "status": "available",
                }
            )

        with pytest.raises(LookupError, match="Game not found"):
            use_case.create_copy(
                {
                    "game_id": 999999,
                    "copy_code": "MISSING-001",
                    "status": "available",
                }
            )

        with pytest.raises(LookupError, match="Game copy not found"):
            use_case.update_copy(999999, {"status": "maintenance"})
