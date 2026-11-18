from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Batch, Student, FeePayment


class Command(BaseCommand):
    help = "Seeds sample batches, students, and payment records for demonstration"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data for Green Valley Tuition Centre...")

        # 1. Create Batches using model's MAX_CAPACITY constant
        batch_a, _ = Batch.objects.get_or_create(
            name="Weekend Morning Batch A",
            defaults={
                "max_capacity": Batch.MAX_CAPACITY,
                "description": "Saturday & Sunday: 9:00 AM - 12:00 PM (Physics & Mathematics)"
            }
        )

        batch_b, _ = Batch.objects.get_or_create(
            name="Weekend Morning Batch B",
            defaults={
                "max_capacity": Batch.MAX_CAPACITY,
                "description": "Saturday & Sunday: 9:00 AM - 12:00 PM (Chemistry & Biology)"
            }
        )

        batch_c, _ = Batch.objects.get_or_create(
            name="Weekend Evening Batch A",
            defaults={
                "max_capacity": Batch.MAX_CAPACITY,
                "description": "Saturday & Sunday: 3:00 PM - 6:00 PM (Comprehensive STEM)"
            }
        )

        batch_d, _ = Batch.objects.get_or_create(
            name="Weekend Evening Batch B",
            defaults={
                "max_capacity": Batch.MAX_CAPACITY,
                "description": "Saturday & Sunday: 3:00 PM - 6:00 PM (Foundation Course)"
            }
        )

        self.stdout.write(self.style.SUCCESS("[OK] Batches created."))

        # 2. Seed Batch B to its maximum capacity to demonstrate full batch rejection
        current_b_count = batch_b.students.count()
        target_capacity = batch_b.max_capacity
        if current_b_count < target_capacity:
            for i in range(current_b_count + 1, target_capacity + 1):
                email = f"student.b{i}@example.com"
                if not Student.objects.filter(email=email).exists():
                    s = Student.objects.create(
                        name=f"Batch-B Student {i}",
                        email=email,
                        phone=f"+91 98765 000{i:02d}",
                        batch=batch_b,
                        total_fee=Decimal("12000.00"),
                    )
                    # Make some partially paid, some fully paid
                    if i % 2 == 0:
                        FeePayment.objects.create(
                            student=s,
                            amount=Decimal("12000.00"),
                            payment_date=timezone.now().date(),
                            notes=f"Full payment - UPI #{1000 + i}"
                        )
                    else:
                        FeePayment.objects.create(
                            student=s,
                            amount=Decimal("6000.00"),
                            payment_date=timezone.now().date(),
                            notes=f"50% advance installment #{1000 + i}"
                        )
            self.stdout.write(self.style.SUCCESS(f"[OK] Batch B seeded to maximum capacity ({target_capacity} students)."))

        # 3. Seed sample students in Batch A with different payment statuses
        samples_a = [
            ("Ananya Sharma", "ananya.sharma@example.com", "+91 98201 11223", Decimal("15000.00"), Decimal("15000.00"), "Cleared fee - eligible for delete"),
            ("Rohan Verma", "rohan.verma@example.com", "+91 98332 22334", Decimal("15000.00"), Decimal("7500.00"), "Pending fee - delete is blocked"),
            ("Pooja Nair", "pooja.nair@example.com", "+91 98453 33445", Decimal("18000.00"), Decimal("0.00"), "Unpaid fee - delete is blocked"),
            ("Kavya Patel", "kavya.patel@example.com", "+91 98765 44556", Decimal("15000.00"), Decimal("10000.00"), "Partial fee paid"),
            ("Aditya Joshi", "aditya.joshi@example.com", "+91 98876 55667", Decimal("15000.00"), Decimal("15000.00"), "Cleared fee - eligible for delete"),
        ]

        for name, email, phone, fee, paid, desc in samples_a:
            if not Student.objects.filter(email=email).exists():
                s = Student.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    batch=batch_a,
                    total_fee=fee,
                )
                if paid > Decimal("0.00"):
                    FeePayment.objects.create(
                        student=s,
                        amount=paid,
                        payment_date=timezone.now().date(),
                        notes=f"Receipt for {desc}"
                    )

        self.stdout.write(self.style.SUCCESS("[OK] Sample students seeded successfully in Batch A."))
        self.stdout.write(self.style.SUCCESS("[SUCCESS] Seeding completed. You can now explore the UI!"))
