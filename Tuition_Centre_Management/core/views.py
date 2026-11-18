from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Count, Q
from .models import Batch, Student, FeePayment
from .forms import StudentForm, FeePaymentForm


class DashboardView(View):
    """
    Dashboard displaying the required 3 assessment metrics:
    1. Total students
    2. Total pending fees
    3. Students per batch
    """
    def get(self, request):
        total_students = Student.objects.count()

        # Total fee minus total payments = pending fees
        total_fee_sum = Student.objects.aggregate(total=Sum("total_fee"))["total"] or Decimal("0.00")
        total_paid_sum = FeePayment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_pending_fees = max(Decimal("0.00"), total_fee_sum - total_paid_sum)

        # Batch counts and occupancy
        batches = Batch.objects.annotate(student_count=Count("students")).order_by("name")
        batch_stats = [
            {
                "batch": b,
                "count": b.student_count,
                "max": b.max_capacity,
                "is_full": b.student_count >= b.max_capacity,
            }
            for b in batches
        ]

        context = {
            "total_students": total_students,
            "total_pending_fees": total_pending_fees,
            "batch_stats": batch_stats,
        }
        return render(request, "core/dashboard.html", context)


class StudentListView(View):
    """
    Displays the list of all students with fee breakdown and action buttons.
    Supports filtering by batch and search by name/email.
    """
    def get(self, request):
        query = request.GET.get("q", "").strip()
        batch_filter = request.GET.get("batch", "")
        status_filter = request.GET.get("status", "")

        students = Student.objects.select_related("batch").prefetch_related("payments").all()

        if query:
            students = students.filter(
                Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
            )
        if batch_filter:
            students = students.filter(batch_id=batch_filter)

        # Attach computed balance and deletion eligibility for UI rendering
        student_items = []
        for s in students:
            can_delete, reason = s.can_be_deleted
            is_pending = s.balance > Decimal("0.00")

            if status_filter == "pending" and not is_pending:
                continue
            if status_filter == "cleared" and is_pending:
                continue

            student_items.append({
                "student": s,
                "total_paid": s.total_paid,
                "balance": s.balance,
                "can_delete": can_delete,
                "delete_reason": reason,
            })

        batches = Batch.objects.all().order_by("name")

        context = {
            "student_items": student_items,
            "batches": batches,
            "selected_batch": batch_filter,
            "selected_status": status_filter,
            "query": query,
            "total_count": len(student_items),
        }
        return render(request, "core/student_list.html", context)


class StudentCreateView(View):
    """
    Adds a new student. Enforces unique email and batch capacity limit.
    """
    def get(self, request):
        form = StudentForm()
        return render(request, "core/student_form.html", {
            "form": form,
            "action_title": "Add New Student",
            "max_capacity": Batch.MAX_CAPACITY,
            "is_create": True,
        })

    def post(self, request):
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"Student '{student.name}' has been successfully enrolled in {student.batch.name}."
            )
            return redirect("student_list")
        return render(request, "core/student_form.html", {
            "form": form,
            "action_title": "Add New Student",
            "max_capacity": Batch.MAX_CAPACITY,
            "is_create": True,
        })


class StudentUpdateView(View):
    """
    Edits an existing student's details or changes their batch.
    """
    def get(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentForm(instance=student)
        return render(request, "core/student_form.html", {
            "form": form,
            "student": student,
            "action_title": f"Edit Student: {student.name}",
            "max_capacity": Batch.MAX_CAPACITY,
            "is_create": False,
        })

    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"Student record for '{student.name}' has been updated successfully."
            )
            return redirect("student_list")
        return render(request, "core/student_form.html", {
            "form": form,
            "student": student,
            "action_title": f"Edit Student: {student.name}",
            "max_capacity": Batch.MAX_CAPACITY,
            "is_create": False,
        })


class StudentDeleteView(View):
    """
    Handles student deletion.
    Enforces safe deletion: A student with a pending balance cannot be deleted,
    and the user is shown an error message explaining why.
    """
    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        can_delete, reason = student.can_be_deleted

        if not can_delete:
            messages.error(request, reason)
            return redirect("student_list")

        student_name = student.name
        student.delete()
        messages.success(
            request,
            f"Student '{student_name}' was successfully deleted since all fee dues were cleared."
        )
        return redirect("student_list")


class RecordPaymentView(View):
    """
    Records a tuition fee payment for a student.
    Enforces that payment amount cannot exceed the student's remaining balance.
    """
    def get(self, request, student_id):
        student = get_object_or_404(Student, pk=student_id)

        if student.balance <= Decimal("0.00"):
            messages.info(
                request,
                f"Student '{student.name}' has already fully paid their fee (Balance: ₹0.00). No further payments needed."
            )
            return redirect("student_list")

        form = FeePaymentForm(student=student)
        return render(request, "core/payment_form.html", {
            "form": form,
            "student": student,
            "payment_history": student.payments.all(),
        })

    def post(self, request, student_id):
        student = get_object_or_404(Student, pk=student_id)
        form = FeePaymentForm(request.POST, student=student)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            payment.save()

            messages.success(
                request,
                f"Successfully recorded payment of ₹{payment.amount:,.2f} for {student.name}. "
                f"Remaining balance is now ₹{student.balance:,.2f}."
            )
            return redirect("student_list")

        return render(request, "core/payment_form.html", {
            "form": form,
            "student": student,
            "payment_history": student.payments.all(),
        })
