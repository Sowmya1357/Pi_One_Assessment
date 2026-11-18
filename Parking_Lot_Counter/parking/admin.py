from django.contrib import admin
from .models import ParkingLot


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = ("id", "total_slots", "occupied_slots", "free_slots", "updated_at")
