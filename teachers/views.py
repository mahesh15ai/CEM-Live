from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import User
from students.models import StudentProfile
from attendance.models import DailyClassAttendance
from .models import TeacherProfile


# ----------------------------------------------------
# 1. Admin: Manage & Register Teachers
# ----------------------------------------------------
@login_required
def manage_teachers(request):
    if not (request.user.is_superuser or getattr(request.user, 'is_admin', False)):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        department = request.POST.get('department', 'Computer Science & IT').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        assigned_course = request.POST.get('assigned_course', '').strip()
        assigned_year = request.POST.get('assigned_year', '').strip()
        assigned_division = request.POST.get('assigned_division', 'A').strip()
        raw_password = request.POST.get('password', 'Teacher@123').strip()

        if User.objects.filter(username=email).exists():
            messages.error(request, f"User with email '{email}' already exists.")
            return redirect('manage_teachers')

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=raw_password,
                    first_name=first_name,
                    last_name=last_name,
                    is_teacher=True,
                    is_staff=True,
                    phone=phone_number
                )

                count = TeacherProfile.objects.count() + 1
                teacher_id = f"VBM-T-{count:03d}"

                TeacherProfile.objects.create(
                    user=user,
                    teacher_id=teacher_id,
                    department=department,
                    phone_number=phone_number,
                    assigned_course=assigned_course,
                    assigned_year=assigned_year,
                    assigned_division=assigned_division
                )

            messages.success(request, f"Teacher Prof. {first_name} {last_name} ({teacher_id}) registered successfully!")
            return redirect('manage_teachers')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('manage_teachers')

    teachers = TeacherProfile.objects.select_related('user').all().order_by('-id')
    return render(request, 'teachers/manage_teachers.html', {'teachers': teachers})


# ----------------------------------------------------
# 2. Teacher Personal Dashboard
# ----------------------------------------------------
@login_required
def teacher_dashboard(request):
    teacher = getattr(request.user, 'teacher_profile', None)
    if not (teacher or request.user.is_superuser or request.user.is_admin):
        messages.error(request, "Access restricted to Class Teachers.")
        return redirect('student_dashboard')

    today = timezone.now().date()
    course = teacher.assigned_course if teacher else 'BCA'
    year = teacher.assigned_year if teacher else 'Third Year'
    division = teacher.assigned_division if teacher else 'A'

    total_students = StudentProfile.objects.filter(course=course, year=year, division=division).count()
    
    today_present = DailyClassAttendance.objects.filter(
        student__course=course, student__year=year, student__division=division,
        date=today, status='Present'
    ).count()

    today_marked = DailyClassAttendance.objects.filter(
        student__course=course, student__year=year, student__division=division,
        date=today
    ).exists()

    context = {
        'teacher': teacher,
        'course': course,
        'year': year,
        'division': division,
        'total_students': total_students,
        'today_present': today_present,
        'today_absent': (total_students - today_present) if today_marked else 0,
        'today_marked': today_marked,
        'today': today,
    }
    return render(request, 'teachers/teacher_dashboard.html', context)