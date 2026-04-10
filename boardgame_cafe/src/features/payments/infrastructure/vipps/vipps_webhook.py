from flask import Blueprint, request, jsonify
from http import HTTPStatus
import logging
from os import getenv

from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.domain.models.payment import PaymentStatus

logger = logging.getLogger(__name__)

vipps_callbacks = Blueprint("vipps_callbacks", __name__)


@vipps_callbacks.route("/api/payments/vipps/callback/v2/payments/<string:order_id>", methods=["POST"])
def vipps_callback(order_id: str):
    try:
        expected = getenv("VIPPS_CALLBACK_AUTH_TOKEN")
        if expected:
            auth = request.headers.get("Authorization")
            if auth != expected:
                logger.warning("Vipps callback auth failed for order=%s", order_id)
                return jsonify({"error": "forbidden"}), HTTPStatus.FORBIDDEN
            
        data = request.get_json(silent=True) or {}
        tx = data.get("transactionInfo") or (data.get("transaction") and data.get("transaction").get("transactionInfo"))
        status = tx.get("status") if tx else None


        repo = PaymentRepository()
        payment = repo.get_by_provider_ref(order_id)
        if payment is None:
            logger.warning("Vipps callback for unknown order_id=%s", order_id)
            return jsonify({"error": "unknown order id"}), HTTPStatus.NOT_FOUND

        if status in ("RESERVE", "RESERVED", "SALE", "CAPTURE"):
            payment.status = PaymentStatus.PAID
        elif status in ("CANCEL", "CANCELLED", "REJECTED", "RESERVE_FAILED", "SALE_FAILED"):
            payment.status = PaymentStatus.FAILED
        elif status == "REFUND":
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PENDING

        payment.provider = "vipps"
        payment.provider_ref = order_id
        repo.update(payment)

        return "", HTTPStatus.OK
    except Exception as exc:
        logger.exception("Error handling Vipps callback: %s", exc)
        return jsonify({"error": "internal error"}), HTTPStatus.INTERNAL_SERVER_ERROR
