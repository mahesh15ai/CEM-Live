import re
import qrcode
from io import BytesIO
from datetime import timedelta

from django.db import models
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    
    department = models.CharField(max_length=100, default='Computer Science & IT')
    course = models.CharField(max_length=50, default='BCA')
    year = models.CharField(max_length=50, default='Third Year')
    division = models.CharField(max_length=10, default='A')
    roll_number = models.IntegerField()
    dob = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='students/photos/', default='students/default.png')
    qr_code = models.ImageField(upload_to='students/qr/', blank=True, null=True)
    
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
        if self.created_at:
            start_year = self.created_at.year
            end_year = str(start_year + 1)[-2:]
            return f"{start_year}-{end_year}"
        return "2026-27"

    def save(self, *args, **kwargs):
        # 1. Auto-generate Student ID
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

        # 2. Save base object first to commit Student ID
        super().save(*args, **kwargs)

        # 3. Auto-generate QR Code directly to Cloudinary WITHOUT local directory creation
        if not self.qr_code and self.student_id:
            qr_text = f"STUDENT_PASS:{self.student_id}"
            qr_img = qrcode.make(qr_text)
            
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            file_name = f"qr_{self.student_id}.png"
            
            # save=False वापरल्याने Vercel डिस्कवर फोल्डर बनवण्याचा प्रयत्न करत नाही
            self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=['qr_code'])


class BannerImage(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=250, blank=True)
    badge_text = models.CharField(max_length=100, default="Annual Event")
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AnnouncementNotice(models.Model):
    notice_text = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid_24h(self):
        return timezone.now() <= self.created_at + timedelta(hours=24)

    def __str__(self):
        return self.notice_text