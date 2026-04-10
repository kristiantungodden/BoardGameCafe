from flask import Blueprint, render_template, request, redirect
import requests as req

mock_vipps = Blueprint("mock_vipps", __name__)

@mock_vipps.route("/mock-vipps/pay", methods=["GET", "POST"])
def mock_pay():
    if request.method == "GET":
        ref = request.args.get("ref", "unknown")
        amount_cents = int(request.args.get("amount", 0))
        return render_template("mock_vipps_pay.html",
            ref=ref,
            amount_nok=f"{amount_cents / 100:.2f}"
        )

    action = request.form.get("action")
    ref = request.form.get("ref")
    status = "RESERVE" if action == "pay" else "CANCEL"
    req.post(
        f"http://localhost:5000/api/payments/vipps/callback/v2/payments/{ref}",
        json={"transactionInfo": {"status": status}},
    )
    return redirect("/")