from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from .models import Student, Batch, FeePayment


class StudentForm(forms.ModelForm):
    """
    Form for adding and editing students.
    Enforces email uniqueness and batch capacity constraints.
    """
    class Meta:
        model = Student
        fields = ["name", "email", "phone", "batch", "total_fee"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Ananya Sharma",
                "required": True,
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., ananya.sharma@example.com",
                "required": True,
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., +91 98765 43210",
                "required": True,
            }),
            "batch": forms.Select(attrs={
                "class": "form-select",
                "required": True,
            }),
            "total_fee": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., 15000.00",
                "step": "0.01",
                "min": "0",
                "required": True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enhance batch dropdown choices to show current capacity status
        batch_choices = [("", "-- Select a Batch --")]
        for batch in Batch.objects.all():
            occupancy = batch.current_occupancy
            status_text = f"{batch.name} ({occupancy}/{batch.max_capacity})"
            if occupancy >= batch.max_capacity:
                if self.instance and self.instance.pk and self.instance.batch_id == batch.id:
                    status_text += " [Current Batch]"
                else:
                    status_text += " [FULL - Cannot Enroll]"
            batch_choices.append((batch.id, status_text))
        self.fields["batch"].choices = batch_choices

    def clean_email(self):
        """
        Email must be unique.
        Normalizes email to lowercase and verifies no duplicate exists.
        """
        email = self.cleaned_data.get("email", "").strip().lower()
        query = Student.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise ValidationError(
                f"A student with the email '{email}' already exists. Please use a unique email address."
            )
        return email

    def clean(self):
        """
        Batch capacity validation:
        Rejects additional enrollments when a batch is full.
        """
        cleaned_data = super().clean()
        batch = cleaned_data.get("batch")

        if batch:
            is_new = self.instance.pk is None
            if is_new:
                if batch.is_full:
                    raise ValidationError({
                        "batch": (
                            f"Batch '{batch.name}' has reached its maximum capacity of "
                            f"{batch.max_capacity} students. Additional enrollments cannot be accepted. "
                            f"Please select a different batch."
                        )
                    })
            else:
                # Editing existing student: check if transferring to a different full batch
                if self.instance.batch_id != batch.id and batch.is_full:
                    raise ValidationError({
                        "batch": (
                            f"Cannot move student to batch '{batch.name}' because it is full "
                            f"({batch.current_occupancy}/{batch.max_capacity} slots occupied). "
                            f"Please select another batch."
                        )
                    })

        return cleaned_data


class FeePaymentForm(forms.ModelForm):
    """
    Form to record a fee payment for a specific student.
    Payment cannot exceed the student's remaining balance.
    """
    class Meta:
        model = FeePayment
        fields = ["amount", "payment_date", "notes"]
        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter payment amount",
                "step": "0.01",
                "min": "0.01",
                "required": True,
            }),
            "payment_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
                "required": True,
            }),
            "notes": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Receipt number / payment mode (e.g., UPI / Cash / Cheque)",
            }),
        }

    def __init__(self, *args, student=None, **kwargs):
        self.student = student
        super().__init__(*args, **kwargs)
        if self.student:
            self.fields["amount"].help_text = (
                f"Current outstanding balance: ₹{self.student.balance:,.2f}. "
                f"Maximum allowable payment is ₹{self.student.balance:,.2f}."
            )

    def clean_amount(self):
        """
        Payments cannot exceed the remaining balance.
        """
        amount = self.cleaned_data.get("amount")
        if self.student and amount is not None:
            current_balance = self.student.balance
            if current_balance <= Decimal("0.00"):
                raise ValidationError("This student has already fully cleared all fees. Balance is ₹0.00.")

            if amount > current_balance:
                raise ValidationError(
                    f"Payment amount of ₹{amount:,.2f} exceeds the remaining balance of "
                    f"₹{current_balance:,.2f}. Payments cannot exceed the outstanding balance."
                )

            if amount <= Decimal("0.00"):
                raise ValidationError("Payment amount must be greater than zero.")

        return amount
