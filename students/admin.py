from django.contrib import admin
from .models import StudentProfile, BannerImage, AnnouncementNotice, AcademicYearRecord

admin.site.register(StudentProfile)

@admin.register(AcademicYearRecord)
class AcademicYearRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_year', 'class_year', 'course', 'division', 'roll_number', 'status')
    list_filter = ('academic_year', 'class_year', 'course', 'status')
    search_fields = ('student__student_id', 'student__user__first_name', 'student__user__last_name', 'roll_number')


@admin.register(BannerImage)
class BannerImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'badge_text', 'is_active', 'created_at')
    list_filter = ('is_active',)

@admin.register(AnnouncementNotice)
class AnnouncementNoticeAdmin(admin.ModelAdmin):
    list_display = ('notice_text', 'is_active', 'created_at')
    list_filter = ('is_active',)