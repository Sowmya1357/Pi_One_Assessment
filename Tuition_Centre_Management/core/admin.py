from django.contrib import admin
from .models import Batch, Student, FeePayment


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("name", "max_capacity", "current_occupancy", "free_slots", "is_full")
    search_fields = ("name",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "batch", "total_fee", "total_paid", "balance", "is_fully_paid")
    list_filter = ("batch",)
    search_fields = ("name", "email", "phone")


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "payment_date", "notes", "created_at")
    list_filter = ("payment_date",)
    search_fields = ("student__name", "student__email", "notes")
