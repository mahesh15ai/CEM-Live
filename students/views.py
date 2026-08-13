import csv
import qrcode
import io
import base64
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

from .models import StudentProfile, BannerImage, AnnouncementNotice, cloudinary_storage_instance
from events.models import EventRegistration
from attendance.models import AttendanceRecord
from certificates.models import Certificate


# ----------------------------------------------------
# 1. READ: Student Directory List
# ----------------------------------------------------
@login_required
def student_list(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied. Admin permissions required.")
        return redirect('event_list')

    search_query = request.GET.get('search', '').strip()
    selected_course = request.GET.get('course', '').strip()

    students = StudentProfile.objects.select_related('user').all().order_by('-created_at')

    if search_query:
        students = students.filter(
            user__first_name__icontains=search_query
        ) | students.filter(
            user__last_name__icontains=search_query
        ) | students.filter(
            student_id__icontains=search_query
        ) | students.filter(
            user__email__icontains=search_query
        )

    if selected_course:
        students = students.filter(course=selected_course)

    context = {
        'students': students,
        'search_query': search_query,
        'selected_course': selected_course,
    }
    return render(request, 'students/student_list.html', context)


# ----------------------------------------------------
# 2. CREATE: Register Single Student (Atomic Transaction)
# ----------------------------------------------------
@login_required
def add_student(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied.")
        return redirect('student_list')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        department = request.POST.get('department', '').strip()
        course = request.POST.get('course', '').strip()
        year = request.POST.get('year', '').strip()
        division = request.POST.get('division', '').strip()
        roll_number = request.POST.get('roll_number', '').strip()
        dob = request.POST.get('dob', '').strip() or None
        photo = request.FILES.get('photo')

        from accounts.models import User
        if User.objects.filter(username=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect('add_student')

        default_password = "Password@123"

        try:
            # Wrap User + StudentProfile creation inside atomic transaction
            with transaction.atomic():
                # 1. Auth User Create
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=default_password,
                    first_name=first_name,
                    last_name=last_name
                )

                # 2. Student Profile Create
                student = StudentProfile(
                    user=user,
                    department=department,
                    course=course,
                    year=year,
                    division=division,
                    roll_number=roll_number,
                    dob=dob
                )

                if photo:
                    student.photo = photo

                # Save base profile to get student_id generated
                student.save()

                # 3. Base64 QR Code Generation (Zero local file write)
                try:
                    qr_text = f"STUDENT_PASS:{student.student_id}"
                    qr_img = qrcode.make(qr_text)
                    buffer = io.BytesIO()
                    qr_img.save(buffer, format='PNG')
                    qr_b64 = base64.b64encode(buffer.getvalue()).decode()
                    
                    student.qr_code = f"data:image/png;base64,{qr_b64}"
                    student.save(update_fields=['qr_code'])
                except Exception:
                    pass

            # 4. Email Credentials Sending
            subject = 'Welcome to Vishwabharti Mahavidyalaya - Student Credentials'
            email_content = f"""
Dear {first_name} {last_name},

Welcome to Vishwabharti Mahavidyalaya Enterprise Portal!

Your student account has been successfully registered. Here are your portal login credentials:

----------------------------------------
Student ID : {student.student_id}
Username   : {email}
Password   : {default_password}
Course     : {course} ({year})
----------------------------------------

Log in to your account here:
https://cem-live-8hjp.vercel.app/accounts/login/

Best Regards,
Vishwabharti Mahavidyalaya, CIDCO, Nanded
            """

            try:
                send_mail(
                    subject=subject,
                    message=email_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                messages.success(request, f"🎓 Student {user.get_full_name()} registered & credentials sent to {email}!")
            except Exception:
                messages.success(request, f"🎓 Student registered successfully! ID: {student.student_id}")

            return redirect('student_list')

        except Exception as e:
            messages.error(request, f"Error registering student: {str(e)}")
            return redirect('add_student')

    return render(request, 'students/add_student.html')


# ----------------------------------------------------
# 3. UPDATE: Edit Student Details (Admin Only)
# ----------------------------------------------------
@login_required
def edit_student(request, student_id):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied.")
        return redirect('student_list')

    student = get_object_or_404(StudentProfile, id=student_id)
    user = student.user

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        new_email = request.POST.get('email', '').strip()

        from accounts.models import User
        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            messages.error(request, "Another user with this email already exists.")
            return render(request, 'students/edit_student.html', {'student': student})

        user.email = new_email
        user.username = new_email
        user.save()

        student.department = request.POST.get('department', '').strip()
        student.course = request.POST.get('course', '').strip()
        student.year = request.POST.get('year', '').strip()
        student.division = request.POST.get('division', '').strip()
        student.roll_number = request.POST.get('roll_number', '').strip()
        
        dob = request.POST.get('dob', '').strip()
        student.dob = dob if dob else None

        if request.FILES.get('photo'):
            student.photo = request.FILES.get('photo')

        student.save()

        messages.success(request, f"✏️ Student {user.get_full_name()} updated successfully!")
        return redirect('student_list')

    return render(request, 'students/edit_student.html', {'student': student})


# ----------------------------------------------------
# 4. DELETE: Remove Student Profile & Account
# ----------------------------------------------------
@login_required
def delete_student(request, student_id):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied.")
        return redirect('student_list')

    student = get_object_or_404(StudentProfile, id=student_id)
    user = student.user
    user.delete()

    messages.success(request, "🗑️ Student record deleted successfully!")
    return redirect('student_list')


# ----------------------------------------------------
# 5. UTILITIES: Bulk Add, Digital Pass, CSV Export
# ----------------------------------------------------
@login_required
def bulk_add_students(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied.")
        return redirect('student_list')

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)
        next(reader, None)

        from accounts.models import User
        count = 0
        for row in reader:
            if len(row) >= 7:
                first_name, last_name, email, course, year, division, roll_number = [x.strip() for x in row[:7]]
                
                if not User.objects.filter(username=email).exists():
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password="Password@123",
                        first_name=first_name,
                        last_name=last_name
                    )
                    StudentProfile.objects.create(
                        user=user,
                        course=course,
                        year=year,
                        division=division,
                        roll_number=roll_number
                    )
                    count += 1

        messages.success(request, f"🎉 Successfully uploaded {count} students!")
        return redirect('student_list')

    return render(request, 'students/bulk_add.html')


@login_required
def student_pass(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)

    qr_content = f"STUDENT_PASS:{student.student_id}"
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#5C061C", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    context = {
        'student': student,
        'qr_b64': qr_b64,
    }
    return render(request, 'students/id_card.html', context)


@login_required
def export_students_excel(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied.")
        return redirect('student_list')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_directory.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student ID', 'First Name', 'Last Name', 'Email', 'Department', 'Course', 'Year', 'Division', 'Roll Number'])

    students = StudentProfile.objects.select_related('user').all()
    for student in students:
        writer.writerow([
            student.student_id,
            student.user.first_name,
            student.user.last_name,
            student.user.email,
            student.department,
            student.course,
            student.year,
            student.division,
            student.roll_number
        ])

    return response


# ----------------------------------------------------
# 6. STUDENT SELF-SERVICE: Profile View & Edit
# ----------------------------------------------------
@login_required
def student_profile_view(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    return render(request, 'students/my_profile.html', {'student': student})


@login_required
def edit_my_profile(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    user = request.user

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.save()

        dob = request.POST.get('dob', '').strip()
        student.dob = dob if dob else None

        if request.FILES.get('photo'):
            student.photo = request.FILES.get('photo')

        student.save()

        messages.success(request, "🎉 Profile updated successfully!")
        return redirect('student_profile_view')

    return render(request, 'students/edit_my_profile.html', {'student': student})


# ----------------------------------------------------
# 7. ADMIN MANAGEMENT: Add Banner & Announcement
# ----------------------------------------------------
@login_required
def add_banner(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied. Admin permissions required.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subtitle = request.POST.get('subtitle', '').strip()
        badge_text = request.POST.get('badge_text', 'Annual Event').strip()
        image = request.FILES.get('image')

        if image and title:
            BannerImage.objects.create(
                title=title,
                subtitle=subtitle,
                badge_text=badge_text,
                image=image
            )
            messages.success(request, "🎉 Banner image uploaded successfully!")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Please provide a Title and Banner Image.")

    return render(request, 'students/add_banner.html')


@login_required
def add_announcement(request):
    is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False)
    if not is_admin:
        messages.error(request, "Access denied. Admin permissions required.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        notice_text = request.POST.get('notice_text', '').strip() or request.POST.get('title', '').strip()

        if notice_text:
            AnnouncementNotice.objects.create(
                notice_text=notice_text,
                is_active=True
            )
            messages.success(request, "📢 Announcement posted! It will remain active for 24 hours.")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Notice text cannot be empty.")

    return render(request, 'students/add_announcement.html')


# ----------------------------------------------------
# 8. STUDENT HOME PAGE / DASHBOARD
# ----------------------------------------------------
@login_required
def student_dashboard(request):
    if request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False):
        return redirect('student_list')

    student = get_object_or_404(StudentProfile, user=request.user)
    
    banners = BannerImage.objects.filter(is_active=True).order_by('-created_at')
    
    last_24_hours = timezone.now() - timedelta(hours=24)
    latest_notice = AnnouncementNotice.objects.filter(
        is_active=True,
        created_at__gte=last_24_hours
    ).order_by('-created_at').first()

    registered_events = EventRegistration.objects.filter(student=student).select_related('event')[:5]
    total_attendance = AttendanceRecord.objects.filter(student=student).count()
    certificates_count = Certificate.objects.filter(student=student).count()

    context = {
        'student': student,
        'banners': banners,
        'latest_notice': latest_notice,
        'registered_events': registered_events,
        'total_attendance': total_attendance,
        'certificates_count': certificates_count,
    }
    return render(request, 'students/student_home.html', context)