from django.db import models
from django.utils import timezone
from accounts.models import User
from students.models import StudentProfile


# 📌 १. मूळ इव्हेंट अटेंडन्स मॉडेल (Event Attendance)
class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    )

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    marked_by = models.CharField(max_length=100, default='System Scanner')

    class Meta:
        ordering = ['-date', '-time']
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.student_id} - {self.date} ({self.status})"


# 📌 २. दैनंदिन वर्ग हजेरी मॉडेल (Daily Classroom Attendance: QR Scanner + Manual)
class DailyClassAttendance(models.Model):
    STATUS_CHOICES = (
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Leave', 'On Leave'),
    )
    METHOD_CHOICES = (
        ('QR_SCAN', 'QR Scanner'),
        ('MANUAL', 'Manual Entry'),
    )

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='daily_class_attendances')
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    method = models.CharField(max_length=15, choices=METHOD_CHOICES, default='MANUAL')
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-marked_at']  # 👈 नवीन नोंदी वर दिसण्यासाठी
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.student_id} | {self.date} | {self.status}"                                                                                                                                                     