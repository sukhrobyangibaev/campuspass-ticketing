class TicketingError(Exception):
    pass


class ValidationError(TicketingError):
    pass


class AvailabilityError(TicketingError):
    pass


class PaymentError(TicketingError):
    pass


class InvalidBookingError(ValidationError):
    def __init__(self, field, value, reason):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field}: {value!r} — {reason}")


class SoldOutError(AvailabilityError):
    def __init__(self, event_name, tier_name, requested, remaining):
        self.event_name = event_name
        self.tier_name = tier_name
        self.requested = requested
        self.remaining = remaining
        super().__init__(
            f"Requested {requested} {tier_name} tickets, only {remaining} remaining"
        )


class DuplicateBookingError(AvailabilityError):
    def __init__(self, email, event_name):
        self.email = email
        self.event_name = event_name
        super().__init__(f"{email} has already booked {event_name}")


class PaymentDeclinedError(PaymentError):
    def __init__(self, gateway_name, reason):
        self.gateway_name = gateway_name
        self.reason = reason
        super().__init__(f"Payment declined by {gateway_name}: {reason}")
