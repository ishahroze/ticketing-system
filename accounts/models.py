from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extends Django's built-in user with a role used for ticket permissions."""

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        AGENT = "agent", "Support Agent"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)

    def is_agent_or_admin(self) -> bool:
        return self.role in (self.Role.AGENT, self.Role.ADMIN)

    def __str__(self):
        return f"{self.username} ({self.role})"
