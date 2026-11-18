# 🎓 Green Valley Tuition Centre — Management Web Application

> **Pi One Technologies — Technical Assessment: Level 2 (Task 1: Mandatory)**  
> **Candidate:** Sowmya R  
> **Application Type:** Front-Office Management Web Application (CRUD, Fee Tracking, Dashboard & Business Rules)

---

## 📌 1. Project Overview & Architecture

**Green Valley Tuition Centre** runs weekend classes with strict classroom capacity constraints. Front-office administrators need a simple, reliable, and professional web portal to manage student enrollments, record fee installments, monitor real-time batch occupancy, and track pending financial dues.

### Architecture Highlights
* **Framework:** Django 5.1 (Python 3.10+)
* **Database:** SQLite (Development / Evaluation ready, swappable to PostgreSQL via settings)
* **Frontend:** Django Templates + Bootstrap 5 (Modern, responsive UI with interactive modals, tooltips, and real-time status badges)
* **Validation Layer:** Dual-layer defense (Strict backend model/form constraints + proactive client-side UI states)

---

## 🚀 2. Installation & Quick Start

### Prerequisites
* Python 3.10 or higher
* `pip` package manager

### Step-by-Step Setup

```bash
# 1. Navigate to the project directory
cd d:\Pi_one\Tuition_Centre_Management

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Environment Variables setup
# Copy the provided template to create your .env
copy .env.example .env

# 4. Apply Database Migrations
python manage.py migrate

# 5. Populate Demo / Seed Data (Batches, Students, Fee records)
python manage.py seed_data

# 6. Run Automated Test Suite
python manage.py test core -v 2

# 7. Start the Development Server
python manage.py runserver
```

Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 🔐 3. Environment Variables (`.env.example`)

The application supports decoupled configuration via environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Set to `False` in production environments. |
| `SECRET_KEY` | Development fallback key | Secret key for cryptographic signing. |
| `ALLOWED_HOSTS` | `*` (dev) / `localhost,127.0.0.1` | Comma-separated list of permitted hostnames. |

---

## 🛡️ 4. Implementation of Business Rules

The system strictly enforces the four mandatory business rules defined in the assessment:

### **Rule (a): Email Must Be Unique**
* **Implementation:** `Student.email` is configured with `unique=True` at the database schema level.
* **Form Validation:** `StudentForm.clean_email()` normalizes the input (`.strip().lower()`), checks for case-insensitive duplicates, and excludes the current student during edits.
* **User Feedback:** Clear, inline error: *"A student with the email '...' already exists. Please use a unique email address."*

### **Rule (b): Max 20 Students per Batch (The 21st is Rejected)**
* **Implementation:** 
  * Each `Batch` has a `max_capacity = 20`.
  * In `Student.clean()` and `StudentForm.clean()`, before creating a new student or transferring an existing student, `batch.current_occupancy` is evaluated.
  * If the count is $\ge 20$, the transaction is blocked.
* **User Feedback:** Clear message: *"Batch '[Name]' has reached its maximum capacity of 20 students. The 21st enrollment is rejected. Please select a different batch."*
* **Proactive UI:** The batch dropdown visually labels full cohorts with `[FULL - Cannot Enroll]`. The Dashboard displays real-time occupancy counts (`count / max`) and a `Full` badge when at capacity.

### **Rule (c): Students with Pending Balance Cannot Be Deleted**
* **Implementation:**
  * Formula: $\text{Balance} = \text{Total Fee} - \sum(\text{Payments})$.
  * `Student.can_be_deleted` returns `(False, reason)` if $\text{Balance} > 0$.
  * Backend deletion views (`StudentDeleteView` and `Student.delete()`) explicitly reject deletion attempts if balance is outstanding.
* **UI Explanation:** 
  * In the student directory, clicking/tapping the Delete button on a student with a pending balance opens a warning modal clearly stating why deletion is blocked (`Cannot delete student '...'. There is a pending balance of ₹X.`) with a shortcut button to record payment.
  * For students with $\text{Balance} = \text{₹0.00}$, clicking Delete opens a confirmation modal to complete the deletion.

### **Rule (d): Payments Cannot Exceed the Balance**
* **Implementation:**
  * In `FeePaymentForm.clean_amount()` and `FeePayment.clean()`, the payment `amount` is compared against `student.balance`.
  * If `amount > student.balance`, validation fails immediately.
* **User Feedback:** Clear error: *"Payment amount of ₹X exceeds the remaining balance of ₹Y. Payments cannot exceed the outstanding balance."*
* **UI Guidance:** The payment interface highlights the exact current balance and caps allowable payment inputs.

---

## 💡 5. Problem-Solving Architecture: Moving a Student to an Already Full Batch

> **Assessment Requirement:** *"In your README, explain how you would move a student to another batch when that batch is already full."*

In real-world tuition center operations, batch capacities are strictly governed by classroom seating, tutor-to-student ratios, and safety regulations. When a student requests a transfer to a batch that has already reached its 20-student ceiling, allowing a 21st student violates Rule (b).

To handle this cleanly in production, we design three architectural solutions:

### Solution 1: Direct Two-Way Student Swap (Atomic Transaction) — *Recommended*
* **Concept:** If Student A in Batch 1 wants to move to Batch 2 (full), and Student B in Batch 2 wants to move to Batch 1, both students can be swapped simultaneously.
* **Database Integrity:** Performed inside an atomic transaction (`with transaction.atomic():`), ensuring that at no intermediate point does either batch exceed 20 students.
```python
from django.db import transaction

def swap_students_between_batches(student_a, student_b):
    with transaction.atomic():
        temp_batch = student_a.batch
        student_a.batch = student_b.batch
        student_b.batch = temp_batch
        
        # Save without triggering intermediate single-student capacity errors
        student_a.save(update_fields=['batch'])
        student_b.save(update_fields=['batch'])
```

### Solution 2: Automated Priority Waitlist (FIFO Queue)
* **Concept:** When Batch 2 is full, Student A is placed on a `BatchWaitlist` queue with a timestamp.
* **Lifecycle:** When an existing student in Batch 2 cancels, drops out, or transfers out (opening a slot), the system triggers an asynchronous event (`signal` or Celery task) to notify the front office and promote the top waitlisted student automatically.

### Solution 3: Supervisor / Center Director Capacity Override with Audit Trail
* **Concept:** For urgent academic exceptions, an authorized Center Director with elevated role-based permissions (`is_superuser` or `CanOverrideBatchCapacity`) can temporarily increment `batch.max_capacity` (e.g., from 20 to 21).
* **Compliance:** The system logs an `AuditLog` entry documenting who approved the exception, timestamp, and justification reason.

---

## 🧪 6. Automated Test Suite & Scenarios

The project includes 9 unit and integration tests in `core/tests.py`:

```bash
python manage.py test core -v 2
```

### Verified Test Cases:
1. `test_rule_a_unique_email_form_validation`: Verifies that duplicate email submission is rejected with an inline error.
2. `test_rule_a_unique_email_case_insensitivity`: Ensures uppercase/lowercase email variants (`Test@` vs `test@`) are correctly caught.
3. `test_rule_b_max_capacity_20_rejection_at_21`: Fills a batch to 20 students; attempts enrollment of the 21st student; verifies rejection.
4. `test_rule_b_cannot_transfer_to_full_batch`: Prevents moving an existing student into another full cohort.
5. `test_rule_c_delete_blocked_when_balance_pending`: Confirms student deletion is blocked when outstanding fees exist and error message is returned.
6. `test_rule_c_delete_allowed_when_balance_zero`: Confirms deletion succeeds cleanly once fee balance is ₹0.00.
7. `test_rule_d_payment_exceeding_balance_rejected`: Confirms overpayments are blocked with an explicit ceiling message.
8. `test_rule_d_multiple_partial_payments_clearance`: Confirms sequential installment payments decrease balance accurately.
9. `test_dashboard_aggregates`: Verifies real-time accuracy of dashboard financial aggregations (`total_students`, `total_pending_fees`, `total_paid_sum`).

---

## 📑 7. Key Assumptions & Limitations

### Assumptions
1. Weekend classes run across fixed weekend batches (Morning & Evening sessions).
2. All tuition fees and payments are in Indian Rupees (₹) with 2 decimal places precision (`DecimalField`).
3. Front office staff handles enrollments; students do not self-register online.

### Limitations & Next Steps
* **Installment Scheduling:** Currently payments are recorded on an ad-hoc basis; next iteration could support structured installment due dates and automated SMS/WhatsApp reminders.
* **Receipt PDF Export:** Adding one-click PDF receipt generation using `ReportLab` or `xhtml2pdf`.
* **Multi-branch Support:** Expanding the schema to support multiple centers/branches under Green Valley.
