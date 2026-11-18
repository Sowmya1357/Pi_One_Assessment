from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ParkingLot
from .serializers import ParkingLotSerializer


class FreeSlotsView(APIView):
    """
    GET /api/slots/
    Returns the total slots, occupied slots, and current number of free slots.
    """
    def get(self, request):
        lot = ParkingLot.get_lot()
        serializer = ParkingLotSerializer(lot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CarEntryView(APIView):
    """
    POST /api/entry/
    Records a car entering the parking lot.
    Rejects entry with 400 Bad Request if the lot is already full.
    """
    def post(self, request):
        with transaction.atomic():
            lot = ParkingLot.get_lot(lock=True)

            if lot.is_full:
                return Response(
                    {
                        "error": "Parking lot is full. Entry rejected because no free slots are available.",
                        **ParkingLotSerializer(lot).data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            lot.occupied_slots += 1
            lot.save(update_fields=["occupied_slots", "updated_at"])

            return Response(
                {
                    "message": "Car entry recorded.",
                    **ParkingLotSerializer(lot).data,
                },
                status=status.HTTP_200_OK,
            )


class CarExitView(APIView):
    """
    POST /api/exit/
    Records a car leaving the parking lot.
    Prevents the occupied count from dropping below zero on an empty lot.
    """
    def post(self, request):
        with transaction.atomic():
            lot = ParkingLot.get_lot(lock=True)

            if lot.is_empty:
                return Response(
                    {
                        "error": "Parking lot is already empty. Cannot record exit because occupied count cannot go below zero.",
                        **ParkingLotSerializer(lot).data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            lot.occupied_slots -= 1
            lot.save(update_fields=["occupied_slots", "updated_at"])

            return Response(
                {
                    "message": "Car exit recorded.",
                    **ParkingLotSerializer(lot).data,
                },
                status=status.HTTP_200_OK,
            )
