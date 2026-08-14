from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Role Identity Flags
    is_admin = models.BooleanField(default=False, verbose_name="Is Admin/Faculty")
    is_teacher = models.BooleanField(default=False, verbose_name="Is Teacher")  # 👈 हे फील्ड आवश्यक आहे
    is_student = models.BooleanField(default=False, verbose_name="Is Student")

    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        if self.is_admin:
            role = "Admin"
        elif self.is_teacher:
            role = "Teacher"
        elif self.is_student:
            role = "Student"
        else:
            role = "User"
        return f"{self.username} ({role})"