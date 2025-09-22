class BookingAdapter:
    def book(self, restaurant_id: str, dt: str, party_size: int) -> dict:
        raise NotImplementedError


class MockBookingAdapter(BookingAdapter):
    def book(self, restaurant_id: str, dt: str, party_size: int) -> dict:
        return {
            "status": "confirmed",
            "restaurant_id": restaurant_id,
            "datetime": dt,
            "party_size": party_size,
        }
