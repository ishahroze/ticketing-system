from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from tickets.models import Category, Ticket

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with demo users, categories, and tickets."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin12345")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created superuser 'admin' / password 'admin12345'"))

        agent, created = User.objects.get_or_create(
            username="agent1",
            defaults={"email": "agent1@example.com", "role": User.Role.AGENT},
        )
        if created:
            agent.set_password("agent12345")
            agent.save()

        customer, created = User.objects.get_or_create(
            username="customer1",
            defaults={"email": "customer1@example.com", "role": User.Role.CUSTOMER},
        )
        if created:
            customer.set_password("customer12345")
            customer.save()

        categories = ["Billing", "Technical Issue", "Account Access", "Feature Request", "General Inquiry"]
        for name in categories:
            Category.objects.get_or_create(name=name)

        if not Ticket.objects.exists():
            Ticket.objects.create(
                title="Cannot log into my account",
                description=(
                    "I've tried resetting my password three times but I still can't log in. "
                    "This is really frustrating since I need access for a client meeting today."
                ),
                created_by=customer,
                category=Category.objects.get(name="Account Access"),
            )
            Ticket.objects.create(
                title="Question about invoice charges",
                description="I noticed an extra charge on my last invoice, could you clarify what it's for?",
                created_by=customer,
                category=Category.objects.get(name="Billing"),
            )
            self.stdout.write(self.style.SUCCESS("Created demo tickets"))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
