import re
from datetime import timedelta

from django.db import models
from django.utils import timezone
from accounts.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    
    department = models.CharField(max_length=100, default='Computer Science & IT')
    course = models.CharField(max_length=50, default='BCA', db_index=True)
    year = models.CharField(max_length=50, default='Third Year', db_index=True)
    division = models.CharField(max_length=10, default='A')
    roll_number = models.IntegerField(db_index=True)
    dob = models.DateField(null=True, blank=True)

    # 📌 storage= काढून टाकल्याने generate_filename ची एरर पूर्णपणे फिक्स होते
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    
    # Base64 QR Code Store (No Local File System dependency)
    qr_code = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"

    @property
    def valid_until(self):
        if self.created_at:
            return self.created_at.date() + timedelta(days=365)
        return None

    @property
    def academic_session(self):
        dt = self.created_at if self.created_at else timezone.now()
        start_year = dt.year if dt.month >= 6 else dt.year - 1
        return f"{start_year}-{str(start_year + 1)[-2:]}"

    def sync_academic_record(self):
        """Ensures an active academic record exists for the student's current session."""
        current_session = self.academic_session
        record, created = AcademicYearRecord.objects.get_or_create(
            student=self,
            academic_year=current_session,
            defaults={
                'class_year': self.year,
                'course': self.course,
                'department': self.department,
                'division': self.division,
                'roll_number': self.roll_number,
                'status': 'Active',
            }
        )
        if not created and record.status == 'Active':
            record.class_year = self.year
            record.course = self.course
            record.department = self.department
            record.division = self.division
            record.roll_number = self.roll_number
            record.save()
        return record

    def save(self, *args, **kwargs):
        # Student ID Auto Generation
        if not self.student_id:
            existing_ids = StudentProfile.objects.filter(
                student_id__startswith='VBM'
            ).values_list('student_id', flat=True)

            max_num = 0
            for sid in existing_ids:
                numbers = re.findall(r'\d+', sid)
                if numbers:
                    num = int(numbers[0])
                    if num > max_num:
                        max_num = num

            next_num = 20260001 if max_num == 0 else max_num + 1

            new_id = f"VBM{next_num}"
            while StudentProfile.objects.filter(student_id=new_id).exists():
                next_num += 1
                new_id = f"VBM{next_num}"

            self.student_id = new_id

        super().save(*args, **kwargs)
        try:
            self.sync_academic_record()
        except Exception:
            pass


class AcademicYearRecord(models.Model):
    CLASS_YEAR_CHOICES = (
        ('First Year', 'First Year (FY)'),
        ('Second Year', 'Second Year (SY)'),
        ('Third Year', 'Third Year (TY)'),
        ('Final Year', 'Final Year (4th Year)'),
        ('M.Sc Part 1', 'M.Sc Part 1'),
        ('M.Sc Part 2', 'M.Sc Part 2'),
        ('Alumni', 'Alumni / Graduated'),
    )

    STATUS_CHOICES = (
        ('Active', 'Active / Current'),
        ('Promoted', 'Promoted'),
        ('Completed', 'Completed / Graduated'),
        ('Detained', 'Detained / Repeater'),
    )

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='academic_records')
    academic_year = models.CharField(max_length=20, db_index=True, help_text="e.g. 2024-25, 2025-26, 2026-27")
    class_year = models.CharField(max_length=50, choices=CLASS_YEAR_CHOICES, default='First Year', db_index=True)
    course = models.CharField(max_length=50, default='BCA')
    department = models.CharField(max_length=100, default='Computer Science & IT')
    division = models.CharField(max_length=10, default='A')
    roll_number = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active', db_index=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-academic_year', 'roll_number']
        unique_together = ('student', 'academic_year')

    def __str__(self):
        return f"{self.student.student_id} | {self.academic_year} | {self.class_year} (Roll: {self.roll_number})"



class BannerImage(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=250, blank=True)
    badge_text = models.CharField(max_length=100, default="Annual Event")
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AnnouncementNotice(models.Model):
    notice_text = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid_24h(self):
        return timezone.now() <= self.created_at + timedelta(hours=24)

    def __str__(self):
        return self.notice_text