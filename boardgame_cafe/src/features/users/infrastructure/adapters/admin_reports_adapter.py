from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_rating_db import GameRatingDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.announcement_db import AnnouncementDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


class SqlAlchemyAdminReportsAdapter:
    def dashboard_stats(self) -> dict[str, Any]:
        user_rows = db.session.query(UserDB.role, func.count(UserDB.id)).group_by(UserDB.role).all()
        user_counts = {"customer": 0, "staff": 0, "admin": 0}
        for role, count in user_rows:
            user_counts[str(role)] = int(count or 0)

        game_copy_rows = db.session.query(GameCopyDB.status, func.count(GameCopyDB.id)).group_by(GameCopyDB.status).all()
        game_copy_counts = {"available": 0, "reserved": 0, "occupied": 0, "maintenance": 0, "lost": 0}
        for status, count in game_copy_rows:
            game_copy_counts[str(status)] = int(count or 0)

        table_rows = db.session.query(TableDB.status, func.count(TableDB.id)).group_by(TableDB.status).all()
        table_counts = {"available": 0, "occupied": 0, "reserved": 0, "maintenance": 0}
        for status, count in table_rows:
            table_counts[str(status)] = int(count or 0)

        booking_rows = db.session.query(BookingDB.status, func.count(BookingDB.id)).group_by(BookingDB.status).all()
        booking_counts = {"confirmed": 0, "seated": 0, "completed": 0, "cancelled": 0, "no_show": 0}
        for status, count in booking_rows:
            booking_counts[str(status)] = int(count or 0)

        return {
            "users_total": sum(user_counts.values()),
            "users_by_role": user_counts,
            "games_total": self._count(GameDB),
            "copies_total": sum(game_copy_counts.values()),
            "copies_by_status": game_copy_counts,
            "tables_total": self._count(TableDB),
            "tables_by_status": table_counts,
            "incidents_total": self._count(IncidentDB),
            "bookings_total": sum(booking_counts.values()),
            "bookings_by_status": booking_counts,
            "open_bookings": booking_counts.get("confirmed", 0) + booking_counts.get("seated", 0),
            "open_incidents": self._count(IncidentDB),
            "published_announcements": int(
                db.session.query(func.count(AnnouncementDB.id)).filter(AnnouncementDB.is_published.is_(True)).scalar() or 0
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def registrations_report(self, days: int) -> list[dict[str, Any]]:
        start_dt, end_dt = self._date_range(days)
        spine = [(start_dt + timedelta(days=i)).date() for i in range(days)]

        rows = (
            db.session.query(
                func.date(UserDB.created_at).label("day"),
                func.count(UserDB.id).label("new_users"),
            )
            .filter(UserDB.created_at >= start_dt, UserDB.created_at <= end_dt)
            .group_by(func.date(UserDB.created_at))
            .all()
        )
        counts_by_day = {r.day: r.new_users for r in rows}

        baseline = (
            db.session.query(func.count(UserDB.id))
            .filter(or_(UserDB.created_at < start_dt, UserDB.created_at.is_(None)))
            .scalar()
            or 0
        )

        result = []
        cumulative = baseline
        for d in spine:
            new = counts_by_day.get(str(d), 0)
            cumulative += new
            result.append({"date": str(d), "new_users": new, "cumulative": cumulative})
        return result

    def revenue_report(self, days: int) -> list[dict[str, Any]]:
        start_dt, end_dt = self._date_range(days)
        spine = [(start_dt + timedelta(days=i)).date() for i in range(days)]

        rows = (
            db.session.query(
                func.date(PaymentDB.created_at).label("day"),
                func.sum(PaymentDB.amount_cents).label("total_cents"),
            )
            .filter(
                PaymentDB.status == "paid",
                PaymentDB.created_at >= start_dt,
                PaymentDB.created_at <= end_dt,
            )
            .group_by(func.date(PaymentDB.created_at))
            .all()
        )
        totals_by_day = {r.day: int(r.total_cents) for r in rows}

        return [{"date": str(d), "total_cents": totals_by_day.get(str(d), 0)} for d in spine]

    def top_games_report(self, days: int) -> dict[str, list[dict[str, Any]]]:
        start_dt, end_dt = self._date_range(days)

        rating_rows = (
            db.session.query(
                GameDB.id.label("game_id"),
                GameDB.title.label("title"),
                func.round(func.avg(GameRatingDB.stars), 2).label("avg_rating"),
                func.count(GameRatingDB.id).label("rating_count"),
            )
            .join(GameRatingDB, GameRatingDB.game_id == GameDB.id)
            .filter(GameRatingDB.created_at >= start_dt, GameRatingDB.created_at <= end_dt)
            .group_by(GameDB.id, GameDB.title)
            .order_by(func.avg(GameRatingDB.stars).desc())
            .limit(3)
            .all()
        )

        booking_rows = (
            db.session.query(
                GameDB.id.label("game_id"),
                GameDB.title.label("title"),
                func.count(GameReservationDB.id).label("booking_count"),
            )
            .join(GameReservationDB, GameReservationDB.requested_game_id == GameDB.id)
            .join(BookingDB, BookingDB.id == GameReservationDB.booking_id)
            .filter(BookingDB.created_at >= start_dt, BookingDB.created_at <= end_dt)
            .group_by(GameDB.id, GameDB.title)
            .order_by(func.count(GameReservationDB.id).desc())
            .limit(3)
            .all()
        )

        return {
            "by_rating": [
                {
                    "game_id": r.game_id,
                    "title": r.title,
                    "avg_rating": float(r.avg_rating),
                    "rating_count": r.rating_count,
                }
                for r in rating_rows
            ],
            "by_bookings": [
                {"game_id": r.game_id, "title": r.title, "booking_count": r.booking_count}
                for r in booking_rows
            ],
        }

    def revenue_csv(self, days: int) -> tuple[str, str]:
        start_dt, end_dt = self._date_range(days)

        daily_rows = (
            db.session.query(
                func.date(PaymentDB.created_at).label("day"),
                func.sum(PaymentDB.amount_cents).label("total_cents"),
                func.count(PaymentDB.id).label("transactions"),
            )
            .filter(PaymentDB.status == "paid", PaymentDB.created_at >= start_dt, PaymentDB.created_at <= end_dt)
            .group_by(func.date(PaymentDB.created_at))
            .order_by(func.date(PaymentDB.created_at))
            .all()
        )

        txn_rows = (
            db.session.query(PaymentDB)
            .filter(PaymentDB.status == "paid", PaymentDB.created_at >= start_dt, PaymentDB.created_at <= end_dt)
            .order_by(PaymentDB.created_at)
            .all()
        )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([f"Revenue Report - last {days} days"])
        writer.writerow([])
        writer.writerow(["DAILY SUMMARY"])
        writer.writerow(["Date", "Transactions", "Total (NOK)"])
        for r in daily_rows:
            writer.writerow([r.day, r.transactions, f"{r.total_cents / 100:.2f}"])
        writer.writerow([])
        writer.writerow(["TRANSACTION LOG"])
        writer.writerow(["Payment ID", "Booking ID", "Amount (NOK)", "Status", "Date"])
        for p in txn_rows:
            writer.writerow([
                p.id,
                p.booking_id,
                f"{p.amount_cents / 100:.2f}",
                p.status,
                p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
            ])

        filename = f"revenue_{start_dt.date()}_{end_dt.date()}.csv"
        return buf.getvalue(), filename

    @staticmethod
    def _date_range(days: int):
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days - 1)
        start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_dt, end_dt

    @staticmethod
    def _count(model, *criteria) -> int:
        query = db.session.query(func.count(model.id))
        for criterion in criteria:
            query = query.filter(criterion)
        result = query.scalar()
        return int(result or 0)
