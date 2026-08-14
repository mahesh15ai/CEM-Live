from django.contrib import admin
from .models import AttendanceRecord, DailyClassAttendance


@admin.register(DailyClassAttendance)
class DailyClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'method', 'marked_by', 'marked_at')
    list_filter = ('status', 'method', 'date', 'student__course', 'student__year', 'student__division')
    search_fields = ('student__student_id', 'student__user__first_name', 'student__user__last_name')
    date_hierarchy = 'date'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'time', 'status', 'marked_by')
    list_filter = ('status', 'date')
    search_fields = ('student__student_id', 'student__user__first_name', 'student__user__last_name')