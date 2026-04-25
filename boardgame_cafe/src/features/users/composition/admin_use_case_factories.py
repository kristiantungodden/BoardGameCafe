from features.users.application.use_cases.admin_catalogue_use_cases import (
    CatalogueManagementUseCase,
)
from features.users.application.use_cases.admin_content_use_cases import (
    ContentManagementUseCase,
)
from features.users.application.use_cases.admin_incident_use_cases import (
    IncidentResolutionUseCase,
)
from features.users.application.use_cases.admin_pricing_use_cases import (
    PricingManagementUseCase,
)
from features.users.application.query_services.admin_reports_query_service import (
    AdminReportsQueryService,
)
from features.users.application.use_cases.admin_reports_use_cases import ReportsUseCase
from features.users.application.use_cases.admin_user_admin_use_cases import (
    UserAdminActionsUseCase,
)
from features.users.application.use_cases.user_use_cases import (
    CreateStewardUseCase,
    ForcePasswordResetUseCase,
    ListUsersUseCase,
)
from features.users.infrastructure.repositories import SqlAlchemyUserRepository
from features.users.infrastructure.adapters.admin_catalogue_adapter import (
    SqlAlchemyAdminCatalogueAdapter,
)
from features.users.infrastructure.adapters.admin_content_adapter import (
    SqlAlchemyAdminContentAdapter,
)
from features.users.infrastructure.adapters.admin_incident_adapter import (
    SqlAlchemyAdminIncidentAdapter,
)
from features.users.infrastructure.adapters.admin_pricing_adapter import (
    SqlAlchemyAdminPricingAdapter,
)
from features.users.infrastructure.adapters.admin_reports_adapter import (
    SqlAlchemyAdminReportsAdapter,
)


def get_create_steward_use_case() -> CreateStewardUseCase:
    return CreateStewardUseCase(SqlAlchemyUserRepository())


def get_list_users_use_case() -> ListUsersUseCase:
    return ListUsersUseCase(SqlAlchemyUserRepository())


def get_force_password_reset_use_case() -> ForcePasswordResetUseCase:
    return ForcePasswordResetUseCase(SqlAlchemyUserRepository())


def get_catalogue_management_use_case() -> CatalogueManagementUseCase:
    return CatalogueManagementUseCase(port=SqlAlchemyAdminCatalogueAdapter())


def get_incident_resolution_use_case() -> IncidentResolutionUseCase:
    return IncidentResolutionUseCase(port=SqlAlchemyAdminIncidentAdapter())


def get_pricing_management_use_case() -> PricingManagementUseCase:
    return PricingManagementUseCase(port=SqlAlchemyAdminPricingAdapter())


def get_content_management_use_case() -> ContentManagementUseCase:
    return ContentManagementUseCase(port=SqlAlchemyAdminContentAdapter())


def get_reports_use_case() -> ReportsUseCase:
    return ReportsUseCase(port=SqlAlchemyAdminReportsAdapter())


def get_reports_query_service() -> AdminReportsQueryService:
    return AdminReportsQueryService(port=SqlAlchemyAdminReportsAdapter())


def get_user_admin_actions_use_case() -> UserAdminActionsUseCase:
    return UserAdminActionsUseCase(user_repo=SqlAlchemyUserRepository())
