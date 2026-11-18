from rest_framework import serializers
from .models import ParkingLot


class ParkingLotSerializer(serializers.ModelSerializer):
    """Serializes the parking lot's total, occupied, and free slot counts."""
    free_slots = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParkingLot
        fields = ["total_slots", "occupied_slots", "free_slots"]
