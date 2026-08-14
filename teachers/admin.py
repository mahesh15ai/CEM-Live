from django.contrib import admin
from .models import TeacherProfile


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('teacher_id', 'get_full_name', 'assigned_course', 'assigned_year', 'assigned_division', 'department')
    search_fields = ('teacher_id', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('assigned_course', 'assigned_year', 'assigned_division', 'department')

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Teacher Name'