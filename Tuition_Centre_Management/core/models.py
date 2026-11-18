from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone


class Batch(models.Model):
    """
    Represents a weekend tuition batch with a defined maximum capacity.
    """
    MAX_CAPACITY = 20

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the batch (e.g., Weekend Morning Batch A)"
    )
    max_capacity = models.PositiveIntegerField(
        default=MAX_CAPACITY,
        help_text="Maximum number of students this batch can accommodate"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description or schedule details"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.current_occupancy}/{self.max_capacity})"

    @property
    def current_occupancy(self) -> int:
        """Returns the number of students currently enrolled in this batch."""
        return self.students.count()

    @property
    def free_slots(self) -> int:
        """Returns remaining available slots."""
        return max(0, self.max_capacity - self.current_occupancy)

    @property
    def is_full(self) -> bool:
        """Returns True if the batch has reached or exceeded max capacity."""
        return self.current_occupancy >= self.max_capacity


class Student(models.Model):
    """
    Represents a student enrolled in Green Valley Tuition Centre.
    Enforces email uniqueness, batch capacity constraints, and safe deletion.
    """
    name = models.CharField(max_length=120, help_text="Full name of student")
    email = models.EmailField(
        unique=True,
        help_text="Unique student email address"
    )
    phone = models.CharField(max_length=20, help_text="Contact phone number")
    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        related_name="students",
        help_text="The batch this student belongs to"
    )
    total_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total agreed tuition fee for this student"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def total_paid(self) -> Decimal:
        """Calculates sum of all recorded payments."""
        result = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return result if result is not None else Decimal("0.00")

    @property
    def balance(self) -> Decimal:
        """
        Calculates remaining balance.
        Balance = total_fee - payments made.
        """
        rem = self.total_fee - self.total_paid
        return max(Decimal("0.00"), rem)

    @property
    def is_fully_paid(self) -> bool:
        return self.balance <= Decimal("0.00")

    @property
    def can_be_deleted(self) -> tuple[bool, str]:
        """
        Safe Deletion: A student with a pending balance cannot be deleted.
        Returns a tuple: (can_delete: bool, reason: str)
        """
        rem_balance = self.balance
        if rem_balance > Decimal("0.00"):
            return (
                False,
                f"Cannot delete student '{self.name}'. There is a pending balance of ₹{rem_balance:,.2f}."
            )
        return True, ""

    def clean(self):
        super().clean()

        # Batch capacity enforcement
        batch = None
        try:
            batch = self.batch
        except (Batch.DoesNotExist, AttributeError):
            batch = None

        if batch:
            is_new = self.pk is None
            if is_new:
                if batch.is_full:
                    raise ValidationError({
                        "batch": f"Batch '{batch.name}' is already full (maximum {batch.max_capacity} students reached). Additional enrollments cannot be added."
                    })
            else:
                existing = Student.objects.filter(pk=self.pk).values("batch_id").first()
                if existing and existing["batch_id"] != self.batch_id:
                    if batch.is_full:
                        raise ValidationError({
                            "batch": f"Cannot move to batch '{batch.name}' because it is already full (maximum {batch.max_capacity} students reached)."
                        })

    def delete(self, *args, **kwargs):
        """
        Block deletion if pending balance exists.
        """
        allowed, reason = self.can_be_deleted
        if not allowed:
            raise ValidationError(reason)
        return super().delete(*args, **kwargs)


class FeePayment(models.Model):
    """
    Records a payment made by a student toward their tuition fee.
    Payments cannot exceed the remaining balance.
    """
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount"
    )
    payment_date = models.DateField(
        default=timezone.now,
        help_text="Date payment was received"
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional receipt number or payment note"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fee Payment"
        verbose_name_plural = "Fee Payments"
        ordering = ["-payment_date", "-created_at"]

    def __str__(self):
        return f"₹{self.amount:,.2f} by {self.student.name} on {self.payment_date}"

    def clean(self):
        super().clean()
        student = None
        try:
            student = self.student
        except (Student.DoesNotExist, AttributeError):
            student = None

        if student and self.amount is not None:
            current_balance = student.balance
            if self.amount > current_balance:
                raise ValidationError({
                    "amount": (
                        f"Payment amount of ₹{self.amount:,.2f} exceeds the remaining balance "
                        f"of ₹{current_balance:,.2f}. Overpayment is not allowed."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
