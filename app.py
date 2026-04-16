import sys
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from campuspass.seed_data import EVENTS

app = Flask(
    __name__,
    template_folder="campuspass/templates",
    static_folder="campuspass/static",
)

# ---------------------------------------------------------------------------
# Helper: try to import student code, print friendly messages if missing
# ---------------------------------------------------------------------------

_exceptions_mod = None
_models_mod = None
_validators_mod = None
_services_mod = None
_gateway_mod = None


def _try_import(module_path, label):
    try:
        mod = __import__(module_path, fromlist=["__name__"])
        # Check if the module has any meaningful content (not just whitespace)
        members = [m for m in dir(mod) if not m.startswith("_")]
        if not members:
            print(f"  ⏳ {label} — file is empty, waiting for your code")
            return None
        print(f"  ✅ {label} — loaded successfully")
        return mod
    except Exception as e:
        print(f"  ❌ {label} — error: {e}")
        return None


def load_student_modules():
    global _exceptions_mod, _models_mod, _validators_mod, _services_mod, _gateway_mod
    print("\n🔍 Loading student modules...")
    _exceptions_mod = _try_import("campuspass.exceptions", "campuspass/exceptions.py")
    _models_mod = _try_import("campuspass.models", "campuspass/models.py")
    _validators_mod = _try_import("campuspass.validators", "campuspass/validators.py")
    _gateway_mod = _try_import("campuspass.gateway", "campuspass/gateway.py")
    _services_mod = _try_import("campuspass.services", "campuspass/services.py")
    print()


# ---------------------------------------------------------------------------
# In-memory event store — built from seed data + student models (if available)
# ---------------------------------------------------------------------------

_event_store: dict = {}  # event_id -> Event object or plain dict
_bookings: list = []  # list of booking records


def _python_files_to_watch() -> list[str]:
    root = Path(__file__).resolve().parent
    return [str(path) for path in root.rglob("*.py")]


def _build_event_store():
    """Build event objects from seed data using student models if available."""
    global _event_store, _bookings
    _event_store = {}
    _bookings = []

    for ev_data in EVENTS:
        if _models_mod and hasattr(_models_mod, "Event") and hasattr(_models_mod, "TicketTier"):
            try:
                tiers = {}
                for tier_id, tier_info in ev_data["tiers"].items():
                    tiers[tier_id] = _models_mod.TicketTier(
                        name=tier_info["name"],
                        price=tier_info["price"],
                        capacity=tier_info["capacity"],
                    )
                event = _models_mod.Event(
                    event_id=ev_data["id"],
                    name=ev_data["name"],
                    date=ev_data["date"],
                    location=ev_data["location"],
                    description=ev_data["description"],
                    tiers=tiers,
                )
                _event_store[ev_data["id"]] = event
                continue
            except Exception as e:
                print(f"  ⚠️  Could not build Event '{ev_data['id']}' from models: {e}")

        # Fallback: store as plain dict
        _event_store[ev_data["id"]] = ev_data


def _event_to_dict(event) -> dict:
    """Convert an Event object or plain dict to a JSON-friendly dict."""
    if isinstance(event, dict):
        # Plain dict fallback
        tiers_out = {}
        for tid, tinfo in event.get("tiers", {}).items():
            tiers_out[tid] = {
                "name": tinfo["name"],
                "price": tinfo["price"],
                "remaining": tinfo["capacity"],
                "capacity": tinfo["capacity"],
            }
        return {
            "id": event["id"],
            "name": event["name"],
            "date": event["date"],
            "location": event["location"],
            "description": event["description"],
            "image": event.get("image", ""),
            "tiers": tiers_out,
            "bookings_enabled": False,
        }
    else:
        # Student-built Event object
        tiers_out = {}
        if hasattr(event, "tiers"):
            for tid, tier in event.tiers.items():
                tiers_out[tid] = {
                    "name": tier.name,
                    "price": tier.price,
                    "remaining": tier.remaining,
                    "capacity": tier.capacity,
                }
        return {
            "id": event.event_id,
            "name": event.name,
            "date": event.date,
            "location": event.location,
            "description": event.description,
            "image": getattr(event, "image", ""),
            "tiers": tiers_out,
            "bookings_enabled": True,
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/events")
def api_events():
    events_out = []
    for ev_data in EVENTS:
        event = _event_store.get(ev_data["id"])
        if event:
            events_out.append(_event_to_dict(event))
    return jsonify(events_out)


@app.route("/api/events/<event_id>")
def api_event_detail(event_id):
    event = _event_store.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(_event_to_dict(event))


@app.route("/api/events/<event_id>/book", methods=["POST"])
def api_book(event_id):
    event = _event_store.get(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    data = request.get_json(silent=True) or {}
    data["event_id"] = event_id

    # --- Task 5: Use student validator if available ---
    if _validators_mod and hasattr(_validators_mod, "parse_booking_request"):
        try:
            booking_req = _validators_mod.parse_booking_request(data)
            email = booking_req.email
            tier_name = booking_req.tier_name
            quantity = booking_req.quantity
        except Exception as e:
            error_info = _extract_error_info(e)
            return jsonify(error_info), 400
    else:
        # Fallback: basic extraction with no validation
        email = data.get("email", "")
        tier_name = data.get("tier_name", "")
        quantity = data.get("quantity", 0)

        if not email or not tier_name:
            return jsonify({"error": "Missing or invalid fields", "error_type": "ValidationError"}), 400

    # --- Task 6: Use checkout service if available ---
    if _services_mod and hasattr(_services_mod, "CheckoutService"):
        try:
            gateway = None
            if _gateway_mod and hasattr(_gateway_mod, "CampusPayGateway"):
                gateway = _gateway_mod.CampusPayGateway()

            service = _services_mod.CheckoutService(gateway=gateway)
            result = service.checkout(event, email, tier_name, quantity, data.get("payment_token", ""))
            _bookings.append(result)
            return jsonify({
                "success": True,
                "message": f"Booked {quantity} {tier_name} ticket(s) for {email}",
                "booking": result,
            })
        except Exception as e:
            traceback.print_exc()
            error_info = _extract_error_info(e)
            status = 409 if "Duplicate" in type(e).__name__ else 400
            return jsonify(error_info), status

    # --- Task 2: Use Event.book() if available ---
    if not isinstance(event, dict) and hasattr(event, "book"):
        try:
            event.book(email, tier_name, quantity)
            booking_record = {
                "email": email,
                "event_id": event_id,
                "event_name": event.name,
                "tier": tier_name,
                "quantity": quantity,
            }
            _bookings.append(booking_record)
            return jsonify({
                "success": True,
                "message": f"Booked {quantity} {tier_name} ticket(s) for {email}",
                "booking": booking_record,
            })
        except Exception as e:
            error_info = _extract_error_info(e)
            status = 409 if "Duplicate" in type(e).__name__ else 400
            return jsonify(error_info), status

    # No student models at all — bookings disabled
    return jsonify({
        "error": "Booking system not yet implemented",
        "error_type": "NotImplemented",
    }), 501


@app.route("/api/bookings")
def api_bookings():
    return jsonify(_bookings)


@app.route("/api/status")
def api_status():
    """Report which student modules are loaded — shown in the UI footer."""
    return jsonify({
        "exceptions": _exceptions_mod is not None and all(
            hasattr(_exceptions_mod, c)
            for c in ("TicketingError", "InvalidBookingError", "SoldOutError", "DuplicateBookingError")
        ),
        "models": _models_mod is not None,
        "validators": _validators_mod is not None,
        "gateway": _gateway_mod is not None,
        "services": _services_mod is not None,
    })


# ---------------------------------------------------------------------------
# Error extraction helper
# ---------------------------------------------------------------------------


def _extract_error_info(exc: Exception) -> dict:
    """Pull structured info from an exception (works for both student and built-in exceptions)."""
    info: dict = {
        "error": str(exc),
        "error_type": type(exc).__name__,
    }

    # If the student added rich attributes, expose them
    for attr in ("event_name", "tier_name", "requested", "remaining",
                 "email", "field", "value", "reason", "deficit",
                 "gateway_name", "reference"):
        if hasattr(exc, attr):
            info[attr] = getattr(exc, attr)

    # Exception chaining info
    if exc.__cause__:
        info["caused_by"] = {
            "error_type": type(exc.__cause__).__name__,
            "error": str(exc.__cause__),
        }

    return info


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_student_modules()
    _build_event_store()
    print("🎫 CampusPass is running at http://localhost:5001\n")
    app.run(
        debug=False,
        use_reloader=True,
        extra_files=_python_files_to_watch(),
        port=5001,
    )
