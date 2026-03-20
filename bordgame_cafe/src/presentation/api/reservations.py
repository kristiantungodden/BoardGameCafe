"""Reservations API endpoints."""

from flask import Blueprint, request, jsonify
from infrastructure.database import SessionLocal
from infrastructure.repositories import (
    SQLAlchemyReservationRepository,
    SQLAlchemyTableRepository,
)
from domain.models import Reservation, ReservationStatus
from application.use_cases.reservation_use_cases import (
    CreateReservationUseCase,
    CancelReservationUseCase,
    ConfirmReservationUseCase,
    CreateReservationRequest,
    CancelReservationRequest,
    ConfirmReservationRequest,
)

reservations_bp = Blueprint("reservations", __name__)


def get_reservation_repository():
    """Get reservation repository with session."""
    db = SessionLocal()
    return SQLAlchemyReservationRepository(db)


def get_table_repository():
    """Get table repository with session."""
    db = SessionLocal()
    return SQLAlchemyTableRepository(db)


@reservations_bp.route("", methods=["GET"])
def list_reservations():
    """
    List all reservations.
    
    Query parameters:
    - skip: Number of reservations to skip (pagination)
    - limit: Maximum number of reservations to return
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    
    try:
        # TODO: Implement actual pagination
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("/<int:reservation_id>", methods=["GET"])
def get_reservation(reservation_id):
    """Get a specific reservation by ID."""
    try:
        reservation_repo = get_reservation_repository()
        reservation = reservation_repo.get_by_id(reservation_id)
        
        if not reservation:
            return jsonify({"error": "Reservation not found"}), 404
        
        return jsonify(reservation.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("", methods=["POST"])
def create_reservation():
    """Create a new reservation."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        reservation_repo = get_reservation_repository()
        table_repo = get_table_repository()
        
        # Get current user (TODO: from JWT token)
        customer_id = 1  # Placeholder
        
        use_case = CreateReservationUseCase(reservation_repo, table_repo)
        
        create_request = CreateReservationRequest(
            customer_id=customer_id,
            table_id=data.get("table_id"),
            party_size=data.get("party_size"),
            reserved_at=data.get("reserved_at"),
            reserved_until=data.get("reserved_until"),
            special_requests=data.get("special_requests", ""),
        )
        
        result = use_case.execute(create_request)
        return jsonify(result.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("/<int:reservation_id>", methods=["PUT"])
def update_reservation(reservation_id):
    """Update an existing reservation."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        reservation_repo = get_reservation_repository()
        reservation = reservation_repo.get_by_id(reservation_id)
        
        if not reservation:
            return jsonify({"error": "Reservation not found"}), 404
        
        # Update only provided fields
        for field, value in data.items():
            if value is not None:
                setattr(reservation, field, value)
        
        reservation_repo.update(reservation)
        return jsonify(reservation.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("/<int:reservation_id>", methods=["DELETE"])
def cancel_reservation(reservation_id):
    """Cancel a reservation."""
    try:
        reservation_repo = get_reservation_repository()
        use_case = CancelReservationUseCase(reservation_repo)
        
        result = use_case.execute(CancelReservationRequest(reservation_id=reservation_id))
        return jsonify(result.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("/<int:reservation_id>/confirm", methods=["POST"])
def confirm_reservation(reservation_id):
    """Confirm a reservation."""
    try:
        reservation_repo = get_reservation_repository()
        use_case = ConfirmReservationUseCase(reservation_repo)
        
        result = use_case.execute(ConfirmReservationRequest(reservation_id=reservation_id))
        return jsonify(result.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@reservations_bp.route("/customer/<int:customer_id>", methods=["GET"])
def get_customer_reservations(customer_id):
    """Get all reservations for a customer."""
    try:
        reservation_repo = get_reservation_repository()
        reservations = reservation_repo.get_by_customer_id(customer_id)
        
        return jsonify([r.dict() for r in reservations]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
