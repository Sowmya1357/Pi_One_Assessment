from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ParkingLot


class ParkingLotAPITests(APITestCase):
    """
    Tests all three endpoints and edge-case scenarios for the Parking Lot Counter API.
    """

    def setUp(self):
        self.slots_url = reverse("free_slots")
        self.entry_url = reverse("car_entry")
        self.exit_url = reverse("car_exit")
        self.total = ParkingLot.TOTAL_SLOTS

    def test_scenario_1_normal_entry_and_exit_flow(self):
        """Scenario 1: Starting empty, recording entries and exits updates free slots accurately."""
        # Initial state: all slots free
        res = self.client.get(self.slots_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_slots"], self.total)
        self.assertEqual(res.data["occupied_slots"], 0)
        self.assertEqual(res.data["free_slots"], self.total)

        # Two cars enter
        res1 = self.client.post(self.entry_url)
        res2 = self.client.post(self.entry_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["occupied_slots"], 2)
        self.assertEqual(res2.data["free_slots"], self.total - 2)

        # One car exits
        res3 = self.client.post(self.exit_url)
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.data["occupied_slots"], 1)
        self.assertEqual(res3.data["free_slots"], self.total - 1)

    def test_scenario_2_reject_entry_when_lot_is_full(self):
        """Scenario 2: When all slots are occupied, an incoming entry is rejected with a clear message."""
        lot = ParkingLot.get_lot()
        lot.occupied_slots = lot.total_slots
        lot.save()

        res = self.client.post(self.entry_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
        self.assertIn("full", res.data["error"].lower())
        self.assertEqual(res.data["occupied_slots"], self.total)
        self.assertEqual(res.data["free_slots"], 0)

    def test_scenario_3_prevent_negative_count_on_empty_lot_exit(self):
        """Scenario 3: Recording an exit when the lot is empty is rejected and never goes below zero."""
        lot = ParkingLot.get_lot()
        self.assertEqual(lot.occupied_slots, 0)

        res = self.client.post(self.exit_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
        self.assertIn("empty", res.data["error"].lower())
        self.assertEqual(res.data["occupied_slots"], 0)
        self.assertEqual(res.data["free_slots"], self.total)

    def test_scenario_4_exit_when_full_frees_one_slot_for_next_entry(self):
        """Scenario 4: When the lot is full and a car exits, 1 slot opens and the next entry succeeds."""
        lot = ParkingLot.get_lot()
        lot.occupied_slots = lot.total_slots
        lot.save()

        # Car leaves full lot -> 1 slot becomes free
        exit_res = self.client.post(self.exit_url)
        self.assertEqual(exit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(exit_res.data["occupied_slots"], self.total - 1)
        self.assertEqual(exit_res.data["free_slots"], 1)

        # Next car can now enter -> lot becomes full again
        entry_res = self.client.post(self.entry_url)
        self.assertEqual(entry_res.status_code, status.HTTP_200_OK)
        self.assertEqual(entry_res.data["occupied_slots"], self.total)
        self.assertEqual(entry_res.data["free_slots"], 0)

    def test_scenario_5_get_slots_reflects_persisted_state(self):
        """Scenario 5: GET /api/slots/ returns the exact persisted state after multiple operations."""
        self.client.post(self.entry_url)
        self.client.post(self.entry_url)
        self.client.post(self.entry_url)
        self.client.post(self.exit_url)

        res = self.client.get(self.slots_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["occupied_slots"], 2)
        self.assertEqual(res.data["free_slots"], self.total - 2)
