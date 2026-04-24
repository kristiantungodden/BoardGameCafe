from __future__ import annotations


class GetFeaturedPicksUseCase:
    def __init__(self, featured_repository):
        self.featured_repository = featured_repository

    def execute(self) -> dict:
        return {
            "top_rated_last_month": self.featured_repository.find_top_rated_last_month(),
            "most_borrowed_last_month": self.featured_repository.find_most_borrowed_last_month(),
        }
