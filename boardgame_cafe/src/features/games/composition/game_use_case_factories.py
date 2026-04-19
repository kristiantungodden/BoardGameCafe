from dataclasses import dataclass

from features.games.application.use_cases.game_copy_use_cases import (
    CreateGameCopyUseCase,
    GetGameCopyByIdUseCase,
    ListGameCopiesUseCase,
    UpdateGameCopyConditionNoteUseCase,
    UpdateGameCopyLocationUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.application.use_cases.game_rating_use_cases import (
    CreateGameRatingUseCase,
    GetAverageRatingByGameIdUseCase,
    GetRatingsByGameIdUseCase,
)
from features.games.application.use_cases.game_tag_use_cases import (
    AttachGameTagUseCase,
    CreateGameTagUseCase,
    ListGameTagsForGameUseCase,
    ListGameTagsUseCase,
    RemoveGameTagUseCase,
)
from features.games.application.use_cases.game_use_cases import GameUseCases
from features.games.infrastructure.repositories.game_copy_repository import (
    GameCopyRepositoryImpl,
)
from features.games.infrastructure.repositories.game_rating_repository import (
    GameRatingRepositoryImpl,
)
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.infrastructure.repositories.game_tag_repository import GameTagRepository
from shared.infrastructure import db


@dataclass(frozen=True)
class GameTagUseCaseBundle:
    create: CreateGameTagUseCase
    list_all: ListGameTagsUseCase
    attach: AttachGameTagUseCase
    remove: RemoveGameTagUseCase
    list_for_game: ListGameTagsForGameUseCase


@dataclass(frozen=True)
class GameCopyUseCaseBundle:
    create: CreateGameCopyUseCase
    list_all: ListGameCopiesUseCase
    get_by_id: GetGameCopyByIdUseCase
    update_status: UpdateGameCopyStatusUseCase
    update_location: UpdateGameCopyLocationUseCase
    update_condition_note: UpdateGameCopyConditionNoteUseCase


@dataclass(frozen=True)
class GameRatingUseCaseBundle:
    create: CreateGameRatingUseCase
    list_by_game: GetRatingsByGameIdUseCase
    get_average: GetAverageRatingByGameIdUseCase


_game_repository = GameRepository()
_tag_repository = GameTagRepository()
_copy_repository = GameCopyRepositoryImpl()
_rating_repository = GameRatingRepositoryImpl()


def get_game_use_cases() -> GameUseCases:
    return GameUseCases(_game_repository)


def get_games_filtered(**kwargs):
    return _game_repository.get_games_filtered(**kwargs)


def get_game_tag_use_cases() -> GameTagUseCaseBundle:
    return GameTagUseCaseBundle(
        create=CreateGameTagUseCase(_tag_repository),
        list_all=ListGameTagsUseCase(_tag_repository),
        attach=AttachGameTagUseCase(_tag_repository),
        remove=RemoveGameTagUseCase(_tag_repository),
        list_for_game=ListGameTagsForGameUseCase(_tag_repository),
    )


def get_game_copy_use_cases() -> GameCopyUseCaseBundle:
    return GameCopyUseCaseBundle(
        create=CreateGameCopyUseCase(_copy_repository),
        list_all=ListGameCopiesUseCase(_copy_repository),
        get_by_id=GetGameCopyByIdUseCase(_copy_repository),
        update_status=UpdateGameCopyStatusUseCase(_copy_repository),
        update_location=UpdateGameCopyLocationUseCase(_copy_repository),
        update_condition_note=UpdateGameCopyConditionNoteUseCase(_copy_repository),
    )


def get_game_copy_by_id_use_case() -> GetGameCopyByIdUseCase:
    return GetGameCopyByIdUseCase(_copy_repository)


def get_game_rating_use_cases() -> GameRatingUseCaseBundle:
    return GameRatingUseCaseBundle(
        create=CreateGameRatingUseCase(_rating_repository),
        list_by_game=GetRatingsByGameIdUseCase(_rating_repository),
        get_average=GetAverageRatingByGameIdUseCase(_rating_repository),
    )


def rollback_games_transaction() -> None:
    db.session.rollback()