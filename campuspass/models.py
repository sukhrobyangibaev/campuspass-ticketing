from dataclasses import dataclass, field
from campuspass.exceptions import InvalidBookingError, SoldOutError, DuplicateBookingError


@dataclass
class TicketTier:
    name: str
    price: float
    capacity: int

    def __post_init__(self):
        self._sold = 0

    @property
    def remaining(self):
        return self.capacity - self._sold

    def reserve(self, quantity, event_name=""):
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise InvalidBookingError("quantity", quantity, "must be a valid integer")

        if quantity <= 0:
            raise InvalidBookingError("quantity", quantity, "must be positive")

        if quantity > self.remaining:
            raise SoldOutError(
                event_name=event_name,
                tier_name=self.name,
                requested=quantity,
                remaining=self.remaining,
            )

        self._sold += quantity


@dataclass
class Event:
    event_id: str
    name: str
    date: str
    location: str
    description: str
    tiers: dict = field(default_factory=dict)

    def __post_init__(self):
        self._booked_emails: set = set()

    def book(self, email, tier_id, quantity):
        if tier_id not in self.tiers:
            raise InvalidBookingError("tier_id", tier_id, "tier does not exist")

        if email in self._booked_emails:
            raise DuplicateBookingError(email=email, event_name=self.name)

        self.tiers[tier_id].reserve(quantity, event_name=self.name)
        self._booked_emails.add(email)
