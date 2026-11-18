from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from core.models import Batch, Student, FeePayment
from core.forms import StudentForm, FeePaymentForm


class TuitionCentreBusinessRuleTests(TestCase):
    """
    Comprehensive test suite verifying all 4 mandatory business rules
    and key dashboard metrics for Green Valley Tuition Centre.
    """

    def setUp(self):
        self.client = Client()

        # Create two test batches
        self.batch_alpha = Batch.objects.create(
            name="Batch Alpha",
            max_capacity=20,
            description="Alpha Weekend Cohort"
        )
        self.batch_beta = Batch.objects.create(
            name="Batch Beta",
            max_capacity=20,
            description="Beta Weekend Cohort"
        )

    # --------------------------------------------------------------------------
    # BUSINESS RULE (a): Email must be unique
    # --------------------------------------------------------------------------
    def test_rule_a_unique_email_form_validation(self):
        """Rule (a): Form validation must reject duplicate email with clear message."""
        Student.objects.create(
            name="First Student",
            email="unique.student@example.com",
            phone="9876543210",
            batch=self.batch_alpha,
            total_fee=Decimal("10000.00")
        )

        form_data = {
            "name": "Second Student",
            "email": "unique.student@example.com",  # Duplicate email
            "phone": "9876543211",
            "batch": self.batch_alpha.id,
            "total_fee": "10000.00"
        }
        form = StudentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("already exists", form.errors["email"][0])

    def test_rule_a_unique_email_case_insensitivity(self):
        """Rule (a): Email uniqueness should also catch casing variants (e.g. Test@ vs test@)."""
        Student.objects.create(
            name="First Student",
            email="case.check@example.com",
            phone="9876543210",
            batch=self.batch_alpha,
            total_fee=Decimal("10000.00")
        )

        form_data = {
            "name": "Duplicate Student",
            "email": "CASE.CHECK@example.com",  # Uppercase variant
            "phone": "9876543212",
            "batch": self.batch_alpha.id,
            "total_fee": "10000.00"
        }
        form = StudentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    # --------------------------------------------------------------------------
    # BUSINESS RULE (b): Batch cannot hold more than 20 students (21st rejected)
    # --------------------------------------------------------------------------
    def test_rule_b_max_capacity_20_rejection_at_21(self):
        """Rule (b): Enrolling 20 students succeeds, the 21st enrollment is rejected."""
        # Enroll exactly 20 students
        for i in range(1, 21):
            Student.objects.create(
                name=f"Student {i}",
                email=f"student{i}@alpha.com",
                phone=f"90000000{i:02d}",
                batch=self.batch_alpha,
                total_fee=Decimal("10000.00")
            )

        self.assertEqual(self.batch_alpha.current_occupancy, 20)
        self.assertTrue(self.batch_alpha.is_full)

        # Attempt to enroll the 21st student via Form
        form_data = {
            "name": "The 21st Student",
            "email": "student21@alpha.com",
            "phone": "9999999999",
            "batch": self.batch_alpha.id,
            "total_fee": "10000.00"
        }
        form = StudentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("batch", form.errors)
        self.assertIn(f"maximum capacity of {self.batch_alpha.max_capacity}", form.errors["batch"][0])

    def test_rule_b_cannot_transfer_to_full_batch(self):
        """Rule (b): An existing student cannot be edited/moved into another full batch."""
        # Fill Batch Beta with 20 students
        for i in range(1, 21):
            Student.objects.create(
                name=f"Beta Student {i}",
                email=f"beta{i}@test.com",
                phone=f"91111111{i:02d}",
                batch=self.batch_beta,
                total_fee=Decimal("10000.00")
            )

        # Student in Batch Alpha
        alpha_student = Student.objects.create(
            name="Alpha Student",
            email="alpha@test.com",
            phone="9222222222",
            batch=self.batch_alpha,
            total_fee=Decimal("10000.00")
        )

        # Attempt to transfer alpha_student into the full Batch Beta
        form = StudentForm(
            data={
                "name": alpha_student.name,
                "email": alpha_student.email,
                "phone": alpha_student.phone,
                "batch": self.batch_beta.id,
                "total_fee": "10000.00",
            },
            instance=alpha_student
        )
        self.assertFalse(form.is_valid())
        self.assertIn("batch", form.errors)
        self.assertIn("full", form.errors["batch"][0])

    # --------------------------------------------------------------------------
    # BUSINESS RULE (c): Student with pending balance cannot be deleted
    # --------------------------------------------------------------------------
    def test_rule_c_delete_blocked_when_balance_pending(self):
        """Rule (c): Attempt to delete student with pending balance must be blocked and explain why."""
        student = Student.objects.create(
            name="Pending Balance Student",
            email="pending@test.com",
            phone="9333333333",
            batch=self.batch_alpha,
            total_fee=Decimal("12000.00")
        )
        # Pay only partial fee of 4000 (Remaining balance = 8000)
        FeePayment.objects.create(
            student=student,
            amount=Decimal("4000.00")
        )
        self.assertEqual(student.balance, Decimal("8000.00"))

        can_del, reason = student.can_be_deleted
        self.assertFalse(can_del)
        self.assertIn("pending balance of ₹8,000.00", reason)

        # Try deleting via POST view
        response = self.client.post(reverse("student_delete", args=[student.id]), follow=True)
        # Student must still exist in DB
        self.assertTrue(Student.objects.filter(id=student.id).exists())

    def test_rule_c_delete_allowed_when_balance_zero(self):
        """Rule (c): Deletion must succeed cleanly once balance is 0."""
        student = Student.objects.create(
            name="Zero Balance Student",
            email="zero@test.com",
            phone="9444444444",
            batch=self.batch_alpha,
            total_fee=Decimal("5000.00")
        )
        # Pay in full
        FeePayment.objects.create(
            student=student,
            amount=Decimal("5000.00")
        )
        self.assertEqual(student.balance, Decimal("0.00"))

        can_del, _ = student.can_be_deleted
        self.assertTrue(can_del)

        # Execute delete via POST view
        response = self.client.post(reverse("student_delete", args=[student.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Student.objects.filter(id=student.id).exists())

    # --------------------------------------------------------------------------
    # BUSINESS RULE (d): Payments cannot exceed the balance
    # --------------------------------------------------------------------------
    def test_rule_d_payment_exceeding_balance_rejected(self):
        """Rule (d): Attempting to pay more than the balance must be rejected."""
        student = Student.objects.create(
            name="Payment Rule Student",
            email="payment.test@example.com",
            phone="9555555555",
            batch=self.batch_alpha,
            total_fee=Decimal("10000.00")
        )

        # Pay 7000 (Balance remaining = 3000)
        FeePayment.objects.create(student=student, amount=Decimal("7000.00"))
        self.assertEqual(student.balance, Decimal("3000.00"))

        # Attempt to record payment of 3500 (> 3000 balance)
        form_data = {
            "amount": "3500.00",
            "payment_date": "2026-11-17",
            "notes": "Overpayment attempt"
        }
        form = FeePaymentForm(data=form_data, student=student)
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)
        self.assertIn("exceeds the remaining balance", form.errors["amount"][0])

    def test_rule_d_multiple_partial_payments_clearance(self):
        """Rule (d): Multiple partial payments correctly calculate decreasing balance."""
        student = Student.objects.create(
            name="Installment Student",
            email="installment@test.com",
            phone="9666666666",
            batch=self.batch_alpha,
            total_fee=Decimal("15000.00")
        )

        # Installment 1: 5000 -> Balance: 10000
        FeePayment.objects.create(student=student, amount=Decimal("5000.00"))
        self.assertEqual(student.balance, Decimal("10000.00"))

        # Installment 2: 5000 -> Balance: 5000
        FeePayment.objects.create(student=student, amount=Decimal("5000.00"))
        self.assertEqual(student.balance, Decimal("5000.00"))

        # Installment 3: Exactly 5000 -> Balance: 0
        FeePayment.objects.create(student=student, amount=Decimal("5000.00"))
        self.assertEqual(student.balance, Decimal("0.00"))
        self.assertTrue(student.is_fully_paid)

    # --------------------------------------------------------------------------
    # DASHBOARD METRICS TEST
    # --------------------------------------------------------------------------
    def test_dashboard_aggregates(self):
        """Verifies dashboard metrics: total students, total pending fees, students per batch."""
        s1 = Student.objects.create(name="S1", email="s1@t.com", phone="1", batch=self.batch_alpha, total_fee=Decimal("10000.00"))
        s2 = Student.objects.create(name="S2", email="s2@t.com", phone="2", batch=self.batch_alpha, total_fee=Decimal("15000.00"))
        s3 = Student.objects.create(name="S3", email="s3@t.com", phone="3", batch=self.batch_beta, total_fee=Decimal("8000.00"))

        # S1 pays 10000, S2 pays 5000, S3 pays 0
        FeePayment.objects.create(student=s1, amount=Decimal("10000.00"))
        FeePayment.objects.create(student=s2, amount=Decimal("5000.00"))

        # Expected:
        # Total students = 3
        # Total fee = 33000
        # Total paid = 15000
        # Total pending = 18000
        # Batch Alpha count = 2, Batch Beta count = 1
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_students"], 3)
        self.assertEqual(response.context["total_pending_fees"], Decimal("18000.00"))
