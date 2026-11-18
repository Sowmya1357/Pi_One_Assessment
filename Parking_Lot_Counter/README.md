# 🚗 Parking Lot Counter API (Django REST Framework)

> **Pi One Technologies — Technical Assessment: Level 2 (Task 3)**  
> **Candidate:** Sowmya R  
> **Design Approach:** Simple Counter Model with Row-Level Locking (Django REST Framework)

---

## 📌 1. Project Overview

A lightweight REST API built with **Django REST Framework** to track real-time slot availability for a 50-slot parking lot. A gate records each car entering and leaving, and operators can query the exact number of free slots at any time.

---

## 🚀 2. Installation & Running the Project

### Prerequisites
* Python 3.10+
* Django & Django REST Framework (`pip install django djangorestframework`)

### Quick Start
```bash
# 1. Navigate to the project folder
cd d:\Pi_one\Parking_Lot_Counter

# 2. (Optional) Create & activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # macOS/Linux

# 3. Copy the environment template
copy .env.example .env

# 4. Run database migrations
python manage.py migrate

# 5. Run the automated test suite
python manage.py test parking -v 2

# 6. Start the development server
python manage.py runserver
```

Open **`http://127.0.0.1:8000/api/slots/`** in your browser to use the interactive DRF Browsable API, or test with `curl` / Postman.

---

## 🔐 3. Environment Variables (`.env.example`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Set to `False` in production. |
| `SECRET_KEY` | Development fallback | Secret key used by Django for cryptographic signing. |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed hostnames. |

---

## 📡 4. API Endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/slots/` | Get `total_slots`, `occupied_slots`, and `free_slots` |
| `POST` | `/api/entry/` | Record a car entering the parking lot |
| `POST` | `/api/exit/` | Record a car leaving the parking lot |

### Example Responses

**1. Check Free Slots (`GET /api/slots/`) — `200 OK`**
```json
{
    "total_slots": 50,
    "occupied_slots": 12,
    "free_slots": 38
}
```

**2. Record Entry (`POST /api/entry/`) — `200 OK`**
```json
{
    "message": "Car entry recorded.",
    "total_slots": 50,
    "occupied_slots": 13,
    "free_slots": 37
}
```

**3. Entry Rejected When Full (`POST /api/entry/`) — `400 Bad Request`**
```json
{
    "error": "Parking lot is full. Entry rejected because no free slots are available.",
    "total_slots": 50,
    "occupied_slots": 50,
    "free_slots": 0
}
```

**4. Record Exit (`POST /api/exit/`) — `200 OK`**
```json
{
    "message": "Car exit recorded.",
    "total_slots": 50,
    "occupied_slots": 12,
    "free_slots": 38
}
```

**5. Exit Rejected When Empty (`POST /api/exit/`) — `400 Bad Request`**
```json
{
    "error": "Parking lot is already empty. Cannot record exit because occupied count cannot go below zero.",
    "total_slots": 50,
    "occupied_slots": 0,
    "free_slots": 50
}
```

---

## 🛡️ 5. How Each Business Rule Is Handled

1. **Configurable Lot Capacity (`TOTAL_SLOTS = 50`):**
   * Defined in a single constant `ParkingLot.TOTAL_SLOTS = 50` in `parking/models.py`. All views, serializers, and tests reference `lot.total_slots` / `ParkingLot.TOTAL_SLOTS` rather than hardcoding `50`.
2. **Reject Entry When Full:**
   * `CarEntryView.post()` checks `lot.is_full` (`occupied_slots >= total_slots`). If true, it returns HTTP `400 Bad Request` with a clear error message and leaves the counter unchanged.
3. **Never Go Below Zero on Empty Lot Exit:**
   * `CarExitView.post()` checks `lot.is_empty` (`occupied_slots <= 0`). If true, it returns HTTP `400 Bad Request` with a clear error message and keeps `occupied_slots` at `0`.
4. **Concurrency Safety (Race Condition Prevention):**
   * Both `CarEntryView` and `CarExitView` wrap the counter read-check-save inside `transaction.atomic()` with `select_for_update()`. If two cars reach the gate at the exact same moment when 1 slot remains, the row lock guarantees only one car gets the last slot and the second receives a clean "lot is full" rejection.

---

## 💡 6. Problem to Solve: What Happens When the Lot Is Full and an Exit Is Recorded?

When the parking lot is completely full (`occupied_slots = 50`, `free_slots = 0`) and a car exits via `POST /api/exit/`:

1. The server starts a database transaction and locks the `ParkingLot` counter row (`select_for_update()`).
2. `CarExitView` verifies `lot.is_empty` — since `occupied_slots` is `50` (not `0`), the exit is valid.
3. `occupied_slots` is decremented by 1 (`50 → 49`) and saved to the database.
4. `free_slots` (`total_slots - occupied_slots`) immediately changes from `0` to `1`, and `lot.is_full` changes from `True` to `False`.
5. The API responds with `200 OK` and `{"message": "Car exit recorded.", "total_slots": 50, "occupied_slots": 49, "free_slots": 1}`.
6. **Effect on the next car:** Because 1 slot is now free, the next `POST /api/entry/` request is accepted (`49 → 50`, `free_slots = 0`) instead of being rejected. If another car tries to enter after that, it is rejected again until another exit occurs.

---

## 🧪 7. Test Scenarios (`parking/tests.py`)

Run all automated tests with:
```bash
python manage.py test parking -v 2
```

| # | Test Scenario | Expected Outcome |
| :--- | :--- | :--- |
| **1** | **Normal Entry & Exit Flow** | Starts at `50` free (`0` occupied). Two entries drop free slots to `48`; one exit brings free slots to `49`. |
| **2** | **Entry When Lot Is Full** | At `50/50` occupied, `POST /api/entry/` returns `400 Bad Request` with `"Parking lot is full..."` and counts stay `50/0`. |
| **3** | **Exit When Lot Is Empty** | At `0/50` occupied, `POST /api/exit/` returns `400 Bad Request` with `"Parking lot is already empty..."` and `occupied_slots` stays `0` (never negative). |
| **4** | **Exit From Full Lot + Re-Entry** | At `50/50` occupied, `POST /api/exit/` succeeds (`49` occupied, `1` free). A subsequent `POST /api/entry/` succeeds (`50` occupied, `0` free). |
| **5** | **Persisted State Query (`GET /api/slots/`)** | After 3 entries and 1 exit, `GET /api/slots/` accurately reports `2` occupied and `48` free. |

---

## 📑 8. Assumptions, Limitations & Next Steps

### Assumptions
* The service manages a single 50-slot parking lot (`pk=1`), auto-initialized on first API request so no manual setup row is needed.
* Gate sensors/operators call `/api/entry/` and `/api/exit/` once per vehicle passage.

### Limitations & Next Steps
* **Audit History:** Approach A stores only the live counter for simplicity. A future iteration could add an `EntryExitLog` table with timestamps and license plate numbers for reporting and billing.
* **Authentication:** In production, gate endpoints should be protected with API key or token authentication so only authorized gate devices can trigger entries/exits.
* **Multiple Lots:** Adding a `lot_id` URL parameter would let the same service manage multiple parking facilities.
