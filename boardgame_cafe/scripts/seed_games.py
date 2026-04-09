import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import create_app
from shared.infrastructure import db
from features.games.infrastructure.database.game_db import GameDB


SEED_GAMES = [
    {
        "title": "Ticket to Ride",
        "min_players": 2,
        "max_players": 5,
        "playtime_min": 120,
        "complexity": Decimal("2.00"),
        "description": "Train routes",
        "image_url": "https://www.outland.no/media/catalog/product/cache/ab0d362431b8ede7989b9ba1a279c0de/8/2/824968717028__c6eeffe288fa356b83f091672c4a4c7c.jpg",
    },
    {
        "title": "Yatzy",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 60,
        "complexity": Decimal("1.20"),
        "description": "Dice rolling game",
        "image_url": "https://play-lh.googleusercontent.com/VTvOurV1NLn_M_2PAuicV-HqSbpbgmhKOIff9EcNj1Oj1dm7EF5APUKHMeLUncnHPbs",
    },
    {
        "title": "Catan",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 180,
        "complexity": Decimal("2.30"),
        "description": "Srategy resource game",
        "image_url": "https://image.api.playstation.com/vulcan/ap/rnd/202209/2812/yzsrapB7edp44te4uowFz62i.png",
    },
    {
        "title": "Monopoly",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 240,
        "complexity": Decimal("1.60"),
        "description": "Money handling",
        "image_url": "https://www.ringo.no/wp-content/uploads/2025/10/802073_6-880x880.jpg",
    },
    {
        "title": "Chutes and Ladders",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 40,
        "complexity": Decimal("1.00"),
        "description": "Dice rolling game",
        "image_url": "https://sandbox.dodona.be/en/activities/203584369/description/BrvnwuB6EfTdPIHc/media/chutes-and-ladders.jpg",
    },
    {
        "title": "Secret Hitler",
        "min_players": 5,
        "max_players": 10,
        "playtime_min": 60,
        "complexity": Decimal("2.50"),
        "description": "Natzi game",
        "image_url": "https://www.outland.no/media/catalog/product/7/1/711746875073__a45f93c3df2f3fcff01ff924782e4a4c.jpg",
    },
    {
        "title": "Ligretto",
        "min_players": 2,
        "max_players": 12,
        "playtime_min": 15,
        "complexity": Decimal("1.30"),
        "description": "Ligretto is a fast-paced, chaotic, and easy-to-learn card game for 2-12 players (depending on combined sets) where everyone plays simultaneously to discard their cards. Players aim to empty their personal 10-card \"Ligretto\" deck into communal piles on the table sorted by color (1-10) before anyone else.",
        "image_url": "https://pricespy-75b8.kxcdn.com/product/standard/280/393659.jpg",
    },
    {
        "title": "UNO",
        "min_players": 2,
        "max_players": 10,
        "playtime_min": 10,
        "complexity": Decimal("1.10"),
        "description": "Uno is the highly popular card game played by millions around the globe. This game is played by matching and then discarding the cards in one's hand till none are left. Since its inception, there are now many versions of Uno that one can play. Here are the rules of the original or classic Uno.",
        "image_url": "https://www.lirumlarumleg.no/cdn/shop/files/Uno.jpg?v=1748880659",
    },
    {
        "title": "Risk",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 240,
        "complexity": Decimal("2.30"),
        "description": "Risk is a classic turn-based strategy board game of military conquest and diplomacy, usually for 2 to 6 players. Players control armies and attempt to take over the world by capturing all 42 territories across six continents, or by achieving a secret, specific mission. Battles are decided through dice rolls.",
        "image_url": "https://d189539ycils2q.cloudfront.net/media/catalog/product/r/i/risk-brettspill.jpg",
    },
    {
        "title": "Trivial Pursuit",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 60,
        "complexity": Decimal("1.70"),
        "description": "Each player has a circular playing piece with six pie-shaped holes. The goal of the game is to collect a pie in each color. the colors correspond to different question categories. The board consists of a circular track with spaces in seven different colors.",
        "image_url": "https://static.partyking.org/fit-in/1300x0/products/original/trivial-pursuit-master-edition-2.jpg",
    },
    {
        "title": "Scrabble",
        "min_players": 2,
        "max_players": 4,
        "playtime_min": 60,
        "complexity": Decimal("2.10"),
        "description": "Scrabble is a classic crossword-style word game for 2-4 players, where participants create words on a 15x15 grid using letter tiles with varying point values. Players compete for the highest score by placing tiles on premium squares to multiply points, aiming to maximize score through vocabulary and strategic placement.",
        "image_url": "https://img.joomcdn.net/9ea28c4c84b9d605888ff02512256e13a66c9275_original.jpeg",
    },
    {
        "title": "Othello",
        "min_players": 2,
        "max_players": 2,
        "playtime_min": 30,
        "complexity": Decimal("1.80"),
        "description": "Othello is a two-player strategy board game played on an 8x8 grid with 64 reversible discs, black on one side and white on the other. The objective is to have the majority of discs showing your color when the last playable empty square is filled, often by capturing opponent pieces through surrounding them (\"outflanking\").",
        "image_url": "https://www.lekolar.no/globalassets/inriver/resources/16796_46068.jpg",
    },
    {
        "title": "Chess",
        "min_players": 2,
        "max_players": 2,
        "playtime_min": 30,
        "complexity": Decimal("2.80"),
        "description": "Chess is a two-player strategic board game played on a 64-square, 8x8 checkered board. Each player commands 16 pieces-one king, one queen, two rooks, two bishops, two knights, and eight pawns-with the objective to checkmate the opponent's king, placing it under inevitable threat of capture.",
        "image_url": "https://www.regencychess.co.uk/images/RCPB232.jpg",
    },
    {
        "title": "7 Wonders",
        "min_players": 3,
        "max_players": 7,
        "playtime_min": 30,
        "complexity": Decimal("2.20"),
        "description": "Three decks of cards featuring images of historical civilizations, armed conflicts, and commercial activity are used in the card drafting game 7 Wonders.",
        "image_url": None,
    },
]


def seed_games() -> tuple[int, int, int]:
    app = create_app()
    inserted = 0
    updated = 0

    with app.app_context():
        existing_games = {game.title: game for game in db.session.query(GameDB).all()}

        for game_data in SEED_GAMES:
            existing = existing_games.get(game_data["title"])
            if existing is None:
                db.session.add(GameDB(**game_data))
                inserted += 1
                continue

            changed = False
            for field in (
                "min_players",
                "max_players",
                "playtime_min",
                "complexity",
                "description",
                "image_url",
            ):
                if getattr(existing, field) != game_data[field]:
                    setattr(existing, field, game_data[field])
                    changed = True

            if changed:
                updated += 1

        if inserted or updated:
            db.session.commit()

        total = db.session.query(GameDB).count()

    return inserted, updated, total


if __name__ == "__main__":
    inserted, updated, total = seed_games()
    print(f"Inserted {inserted} mock games, updated {updated}. Total games now: {total}")
