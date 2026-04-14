# 🎫 CampusPass — Event Ticketing System

You are building the backend logic for **CampusPass**, a campus event ticketing platform. Students can browse upcoming events — concerts, hackathons, workshops, comedy nights — and book tickets. The frontend and server are already built. Your job is to implement the Python classes that power the booking system, with a focus on **robust exception handling**.

## Setup

```bash
git clone <REPO_URL>
cd campuspass-ticketing
pip install -r requirements.txt
python app.py
```

Open http://localhost:5001 in your browser.

## How This Works

- You ONLY modify Python files inside `campuspass/` — specifically the files listed in each task
- Do NOT touch `app.py`, `seed_data.py`, or anything in `templates/` or `static/`
- After making changes, stop the server (`Ctrl+C`), then run `python app.py` again and refresh the browser

The footer at the bottom of the page shows which modules are loaded (green dot) or still empty (gray dot).

---

## Tasks

### Task 1 — Define Custom Exceptions (Easy)
**File:** `campuspass/exceptions.py`

The ticketing system needs its own exception types instead of using generic Python exceptions like `ValueError`.

Create the following exception classes:

- `TicketingError` — the base exception for all CampusPass errors. Inherits from `Exception`.
- `InvalidBookingError` — raised when booking data is invalid (bad email, wrong tier, etc.). Inherits from `TicketingError`.
- `SoldOutError` — raised when there are not enough tickets remaining. Inherits from `TicketingError`.
- `DuplicateBookingError` — raised when the same email tries to book the same event twice. Inherits from `TicketingError`.

Each exception only needs to inherit from the correct parent. No extra logic is needed yet.

**Verify:** The footer in the browser should show a green dot next to `exceptions.py`. The app still won't accept bookings yet — that comes in Task 2.

---

### Task 2 — Build the Event and TicketTier Models (Easy+)
**File:** `campuspass/models.py`

Now make the event and ticket data come alive. Implement two classes:

**`TicketTier`** — represents one ticket type for an event (e.g., "VIP", "General"). Use a dataclass with these fields:
- `name` (str) — display name of the tier
- `price` (float) — ticket price
- `capacity` (int) — total number of tickets

Use `__post_init__` to initialize an internal `_sold` counter (starts at 0) to track how many tickets have been reserved.

Add a `remaining` property that returns how many tickets are still available.

Add a `reserve(quantity)` method that:
- Raises `InvalidBookingError` if `quantity` is not a positive integer (e.g., 0, -1, or a non-integer like `"two"`)
- Raises `SoldOutError` if `quantity > remaining`
- Otherwise, increases `_sold` by `quantity`

**`Event`** — represents an event with multiple ticket tiers. Use a dataclass with these fields:
- `event_id` (str)
- `name` (str)
- `date` (str)
- `location` (str)
- `description` (str)
- `tiers` (dict mapping tier ID strings to `TicketTier` objects)

Use `__post_init__` to initialize an internal `_booked_emails` set (starts empty) to track which emails have already booked this event.

Add a `book(email, tier_id, quantity)` method. It should:
- Raise `InvalidBookingError` if the tier ID (the dictionary key, e.g. `"general"`, `"vip"`) doesn't exist in `self.tiers`
- Raise `DuplicateBookingError` if this email has already booked this event
- Otherwise, reserve the tickets on the correct tier and record the booking

You will need to import your exceptions from `campuspass.exceptions` and you will need to track booked emails and sold tickets internally.

**Verify:** Event cards should now show a "Book Tickets" button instead of "Booking not available". You can successfully book tickets, and the remaining count decreases. Trying to book with a bad tier name, zero quantity, or the same email twice should show error messages.

---

### Task 3 — Build an Exception Hierarchy (Medium)
**File:** `campuspass/exceptions.py`

Right now all exceptions inherit directly from `TicketingError`. Restructure them into categories so the system can handle related errors as a group.

Create intermediate exception classes:

- `ValidationError` — parent for errors about invalid input. Inherits from `TicketingError`.
- `AvailabilityError` — parent for errors about tickets not being available. Inherits from `TicketingError`.
- `PaymentError` — parent for errors during payment. Inherits from `TicketingError`.

Then update the existing exceptions:
- `InvalidBookingError` should now inherit from `ValidationError`
- `SoldOutError` should now inherit from `AvailabilityError`
- `DuplicateBookingError` should now inherit from `AvailabilityError`

And add one new exception:
- `PaymentDeclinedError` — inherits from `PaymentError`

Your models from Task 2 should continue working without changes since the hierarchy is backward-compatible.

**Verify:** Everything from Task 2 still works. The error type shown in error messages should still display the specific exception name (e.g., `SoldOutError`, not `AvailabilityError`).

---

### Task 4 — Make Exceptions Carry Rich Data (Medium+)
**File:** `campuspass/exceptions.py` (and update raises in `campuspass/models.py` to pass the new arguments)

Generic error messages like "not enough tickets" aren't helpful. Make your exceptions store structured data so the UI can display detailed feedback.

Update your exception classes to accept and store relevant attributes via custom `__init__` methods. Each should call `super().__init__(...)` with a human-readable message. Here's what each exception should carry:

- **`InvalidBookingError`** — `field` (which input was wrong), `value` (what was provided), `reason` (why it's wrong)
- **`SoldOutError`** — `event_name`, `tier_name`, `requested` (how many were requested), `remaining` (how many are left)
- **`DuplicateBookingError`** — `email`, `event_name`
- **`PaymentDeclinedError`** — `gateway_name`, `reason`

After updating the exceptions, update your `TicketTier.reserve()` and `Event.book()` methods to pass the appropriate data when raising these exceptions.

**Verify:** When a booking fails, the error panel now shows structured details — for example, "Requested 5 VIP tickets, only 3 remaining" with labeled fields like `event name`, `tier name`, `requested`, `remaining` shown below the error message.

---

### Task 5 — Validate Input Using EAFP (Advanced)
**File:** `campuspass/validators.py`

The booking form sends raw data from the browser. Right now the server does minimal checking. Build a proper validator using the **EAFP** (Easier to Ask Forgiveness than Permission) style.

Create a `BookingRequest` dataclass with fields: `email` (str), `tier_name` (str), `quantity` (int).

Implement a function `parse_booking_request(data: dict) -> BookingRequest` that takes a dictionary like:

```python
{
    "email": "student@university.edu",
    "tier_name": "VIP",
    "quantity": "2",        # note: may arrive as a string from the form
    "event_id": "evt-001"   # added by the server, you can ignore it
}
```

The function should:

- Extracts `email`, `tier_name`, and `quantity` from the dictionary
- Uses EAFP style (try/except) for extraction and type conversion — don't check types before converting, just try and handle the failure
- Strips whitespace from strings and lowercases the email
- Validates business rules: email must contain `@`, quantity must be positive
- Raises `InvalidBookingError` with appropriate `field`, `value`, and `reason` for any problem
- Uses exception chaining (`raise ... from ...`) when wrapping lower-level exceptions like `KeyError` or `ValueError`
- Returns a `BookingRequest` on success

**Verify:** Try booking with an empty email, a non-numeric quantity, or missing fields. The error messages should be specific — telling you exactly which field failed and why, with the original error shown as "Caused by" in the error panel.

---

### Task 6 — Build the Checkout Service with Exception Chaining (Advanced+)
**Files:** `campuspass/gateway.py` and `campuspass/services.py`

Build the full checkout pipeline that ties everything together: validate input → reserve tickets → charge payment → confirm booking. If any step fails, earlier steps must be rolled back properly.

**In `campuspass/gateway.py`**, implement a `CampusPayGateway` class with a `charge(amount, token)` method that simulates a payment processor:
- If token starts with `"tok_valid"` — return a dict with `"reference"` (any unique string) and `"amount"`
- If token starts with `"tok_decline"` — raise `PaymentDeclinedError`
- If token starts with `"tok_error"` — raise a `ConnectionError` (simulating a gateway outage)
- For any other token — raise `PaymentDeclinedError` with reason `"invalid token"`

**In `campuspass/services.py`**, implement a `CheckoutService` class:
- Constructor takes a `gateway` parameter (a `CampusPayGateway` instance, or `None`)
- Implement a `checkout(event, email, tier_name, quantity, payment_token)` method that:
  1. Validates the input (use `parse_booking_request` from validators)
  2. Reserves tickets on the event (calls `event.book(...)`)
  3. Calculates the total price from the tier
  4. Charges the payment through the gateway (if the gateway is not `None` and the price is greater than 0)
  5. Returns a booking summary dict on success with keys: `email`, `event_id`, `event_name`, `tier`, `quantity`, and `total_price`
- If the payment fails after tickets were reserved, you must **release those tickets back** (undo the reservation) before re-raising the error
  - To support this, you'll need to add a `release(quantity)` method to `TicketTier` that decreases `_sold` by the given amount, and an `unbook(email)` method to `Event` that removes the email from `_booked_emails`
- When catching `ConnectionError` from the gateway, wrap it in a `PaymentError` using `raise ... from ...` to preserve the original cause
- When catching `PaymentDeclinedError`, release the tickets and re-raise it as-is using bare `raise`

**Verify:** 
- Book a free event (like HackCampus) — should work without payment
- Book a paid event with token `tok_valid_1234` — should succeed
- Try `tok_decline_nope` — should fail with `PaymentDeclinedError` and tickets should NOT be deducted
- Try `tok_error_crash` — should fail with `PaymentError` and show "Caused by: ConnectionError" in the error panel, and tickets should NOT be deducted

---

## Acknowledgment

This tutorial format was suggested by Maftuna Ro'zmetova (SE1) - thank you for the idea!
