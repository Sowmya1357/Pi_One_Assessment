# 🚀 Pi One Technologies — Technical Assessment: Level 2

**Candidate:** Sowmya R  
**Submission Deadline:** Thursday, 19 November 2026, 6:00 PM  
**Issued by:** Pi One Technologies, Hiring Team

---

## 📂 Repository Structure

This repository contains the complete implementation for **Task 1 (Mandatory)** and **Task 3 (Chosen Elective)**:

```text
Pi_one/
├── Tuition_Centre_Management/      # Task 1: Tuition Centre Management (Django Full-Stack)
│   ├── config/                     # Settings, URLs, and project configuration
│   ├── core/                       # Models, Forms, Views, Tests, Admin, Seed Data
│   ├── templates/                  # Bootstrap 5 Responsive Web Interface
│   ├── .env.example                # Sample environment configuration
│   └── README.md                   # Full documentation, business rule handling & Q&A
│
├── Parking_Lot_Counter/            # Task 3: Parking Lot Counter API (Django REST Framework)
│   ├── config/                     # Settings, URLs, and DRF routing
│   ├── parking/                    # Counter Model, Serializer, API Views, Tests, Admin
│   ├── .env.example                # Sample environment configuration
│   └── README.md                   # API docs, full lot exit behavior & test scenarios
│
├── .gitignore                      # Excludes venv, sqlite3, secrets, pycache
└── README.md                       # Main assessment entry point
```

---

## 📌 Task Summary

### Task 1: Tuition Centre Management (CRUD + Dashboard + Business Rules)
A front-office web application for Green Valley Tuition Centre to manage weekend cohorts, student enrollments, and tuition fee payments.
* **Stack:** Python 3.10+, Django 5.1, Bootstrap 5, SQLite
* **Features:**
  * Student CRUD (Add, List, Edit, Delete).
  * Fee collection and balance computation ($\text{Balance} = \text{Total Fee} - \text{Payments}$).
  * Clean Dashboard: Total students, total pending fees, and students per batch (with `count / max` and `Full` indicator).
* **Strict Business Rules Enforced:**
  1. **Rule (a):** Unique student email address.
  2. **Rule (b):** Maximum batch capacity (`MAX_CAPACITY = 20`); additional enrollments rejected.
  3. **Rule (c):** Safe deletion policy — students with pending fee balances cannot be deleted; the UI informs the user and provides a payment shortcut.
  4. **Rule (d):** Payments cannot exceed remaining balance.
* **Testing:** 9 automated unit/integration tests covering all rules (`python manage.py test core -v 2`).
* 👉 **[Full Task 1 Documentation & Setup Guide](Tuition_Centre_Management/README.md)**

---

### Task 3: Parking Lot Counter (Django REST Framework)
A real-time REST API for a 50-slot parking facility with gate entry/exit recording and slot availability querying.
* **Stack:** Python 3.10+, Django REST Framework, SQLite
* **Endpoints:**
  * `GET /api/slots/`: Returns `total_slots`, `occupied_slots`, and `free_slots`.
  * `POST /api/entry/`: Records entry; rejects with `400 Bad Request` if lot is full (`free_slots == 0`).
  * `POST /api/exit/`: Records exit; rejects with `400 Bad Request` if lot is empty (never drops below 0).
* **Concurrency Safety:** Row-level locking via `select_for_update()` inside `transaction.atomic()`.
* **Testing:** 5 automated API tests covering lifecycle, edge cases, and full lot exit flow (`python manage.py test parking -v 2`).
* 👉 **[Full Task 3 Documentation & Setup Guide](Parking_Lot_Counter/README.md)**

---

## ⚡ Quick Start

### 1. Run Task 1 (Tuition Centre Management)
```bash
cd Tuition_Centre_Management
copy .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py test core -v 2
python manage.py runserver 8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

### 2. Run Task 3 (Parking Lot Counter API)
```bash
cd Parking_Lot_Counter
copy .env.example .env
python manage.py migrate
python manage.py test parking -v 2
python manage.py runserver 8001
```
Open **`http://127.0.0.1:8001/api/slots/`** in your browser.

---

## 🛡️ Repository Hygiene & Submission Compliance
* ✅ `node_modules` and virtual environments excluded (`.gitignore`).
* ✅ `db.sqlite3` binaries excluded.
* ✅ No hardcoded credentials or secret keys (templates provided in `.env.example`).
* ✅ Comprehensive `README.md` in root and each project folder.
* ✅ Fully automated test suites with 100% passing tests for both tasks.
