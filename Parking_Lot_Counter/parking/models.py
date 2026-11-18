from django.db import models


class ParkingLot(models.Model):
    """
    Tracks the current occupancy of the parking lot using a simple counter.
    Update TOTAL_SLOTS in this one place if the lot capacity changes.
    """
    TOTAL_SLOTS = 50

    total_slots = models.PositiveIntegerField(default=TOTAL_SLOTS)
    occupied_slots = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Parking Lot ({self.free_slots}/{self.total_slots} free)"

    @property
    def free_slots(self) -> int:
        """Number of currently available parking slots."""
        return self.total_slots - self.occupied_slots

    @property
    def is_full(self) -> bool:
        """True when all slots are occupied."""
        return self.occupied_slots >= self.total_slots

    @property
    def is_empty(self) -> bool:
        """True when no cars are in the lot."""
        return self.occupied_slots <= 0

    @classmethod
    def get_lot(cls, lock: bool = False):
        """
        Returns the single parking lot counter record (auto-creates it on first use).
        When lock=True inside transaction.atomic(), locks the row to prevent
        race conditions if two cars enter or leave at the exact same moment.
        """
        if lock:
            lot = cls.objects.select_for_update().filter(pk=1).first()
            if lot is None:
                lot, _ = cls.objects.get_or_create(
                    pk=1,
                    defaults={"total_slots": cls.TOTAL_SLOTS, "occupied_slots": 0},
                )
                lot = cls.objects.select_for_update().get(pk=lot.pk)
            return lot

        lot, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"total_slots": cls.TOTAL_SLOTS, "occupied_slots": 0},
        )
        return lot
