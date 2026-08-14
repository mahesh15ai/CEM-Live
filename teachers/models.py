from django.db import models
from accounts.models import User

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    teacher_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, default='Computer Science & IT')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Class Allocation
    assigned_course = models.CharField(max_length=50, blank=True, null=True)   # BCA, B.Sc
    assigned_year = models.CharField(max_length=50, blank=True, null=True)     # First Year, Third Year
    assigned_division = models.CharField(max_length=10, default='A')           # A, B
    academic_year = models.CharField(max_length=20, default="2026-27")

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.assigned_course} {self.assigned_year} - {self.assigned_division})"