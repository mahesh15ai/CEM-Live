import base64
import csv
from datetime import timedelta
import io
import threading

from attendance.models import AttendanceRecord
from certificates.models import Certificate
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from events.models import EventRegistration
import qrcode

from .models import AnnouncementNotice, BannerImage, StudentProfile


# ----------------------------------------------------
# Helper: Async Email Dispatch (Zero Request Delay)
# ----------------------------------------------------
def send_mail_async(subject, message, recipient_list):
  """Sends emails in a separate thread so web responses stay instantaneous."""

  def _send():
    try:
      send_mail(
          subject=subject,
          message=message,
          from_email=settings.DEFAULT_FROM_EMAIL,
          recipient_list=recipient_list,
          fail_silently=True,
      )
    except Exception:
      pass

  threading.Thread(target=_send, daemon=True).start()


# ----------------------------------------------------
# Helper: Generate Strong Random Password
# ----------------------------------------------------
def generate_student_password():
  return get_random_string(
      length=10,
      allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789@#$',
  )


# ----------------------------------------------------
# Helper: Admin Permission Check
# ----------------------------------------------------
def is_admin_user(user):
  return (
      user.is_superuser or user.is_staff or getattr(user, 'is_admin', False)
  )


# ----------------------------------------------------
# 1. READ: Student Directory List (Optimized & Paginated)
# ----------------------------------------------------
@login_required
def student_list(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied. Admin permissions required.')
    return redirect('event_list')

  search_query = request.GET.get('search', '').strip()
  selected_course = request.GET.get('course', '').strip()

  students_queryset = (
      StudentProfile.objects.select_related('user')
      .all()
      .order_by('-created_at')
  )

  if search_query:
    students_queryset = (
        students_queryset.filter(user__first_name__icontains=search_query)
        | students_queryset.filter(user__last_name__icontains=search_query)
        | students_queryset.filter(student_id__icontains=search_query)
        | students_queryset.filter(user__email__icontains=search_query)
    )

  if selected_course:
    students_queryset = students_queryset.filter(course=selected_course)

  # ⚡ 25 Students per page
  paginator = Paginator(students_queryset, 25)
  page_number = request.GET.get('page')

  try:
    students = paginator.page(page_number)
  except PageNotAnInteger:
    students = paginator.page(1)
  except EmptyPage:
    students = paginator.page(paginator.num_pages)

  context = {
      'students': students,
      'search_query': search_query,
      'selected_course': selected_course,
  }
  return render(request, 'students/student_list.html', context)


# ----------------------------------------------------
# 2. CREATE: Register Single Student (Unique Password & Async Email)
# ----------------------------------------------------
@login_required
def add_student(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied.')
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
      messages.error(request, 'A user with this email already exists.')
      return redirect('add_student')

    random_password = generate_student_password()

    try:
      with transaction.atomic():
        # 1. Create Auth User
        user = User.objects.create_user(
            username=email,
            email=email,
            password=random_password,
            first_name=first_name,
            last_name=last_name,
        )

        # 2. Create Student Profile
        student = StudentProfile(
            user=user,
            department=department,
            course=course,
            year=year,
            division=division,
            roll_number=roll_number,
            dob=dob,
        )

        if photo:
          student.photo = photo

        student.save()

        # 3. Base64 QR Code Generation
        try:
          qr_text = f'STUDENT_PASS:{student.student_id}'
          qr_img = qrcode.make(qr_text)
          buffer = io.BytesIO()
          qr_img.save(buffer, format='PNG')
          qr_b64 = base64.b64encode(buffer.getvalue()).decode()

          student.qr_code = f'data:image/png;base64,{qr_b64}'
          student.save(update_fields=['qr_code'])
        except Exception:
          pass

      # 4. Async Email Dispatch
      subject = (
          'Welcome to Vishwabharti Mahavidyalaya - Student Portal Credentials'
      )
      email_content = f"""Dear {first_name} {last_name},

Welcome to Vishwabharti Mahavidyalaya Enterprise Portal!

Your student account has been successfully created. Here are your portal credentials:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Student ID : {student.student_id}
Username   : {email}
Password   : {random_password}
Course     : {course} ({year})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Login URL: https://cem-live-w7jl.vercel.app/accounts/login/

Security Advice:
1. Please do not share these credentials with anyone.
2. After logging in, you can change your password anytime via Profile Settings.

Best Regards,
Vishwabharti Mahavidyalaya, CIDCO, Nanded
"""
      send_mail_async(subject, email_content, [email])

      messages.success(
          request,
          f'🎓 Student {user.get_full_name()} registered successfully! Credentials sent to {email}.',
      )
      return redirect('student_list')

    except Exception as e:
      messages.error(request, f'Error registering student: {e!s}')
      return redirect('add_student')

  return render(request, 'students/add_student.html')


# ----------------------------------------------------
# 3. UPDATE: Edit Student Details (Admin Only + Photo Deletion)
# ----------------------------------------------------
@login_required
def edit_student(request, student_id):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied.')
    return redirect('student_list')

  student = get_object_or_404(
      StudentProfile.objects.select_related('user'), id=student_id
  )
  user = student.user

  if request.method == 'POST':
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    new_email = request.POST.get('email', '').strip()

    from accounts.models import User

    if User.objects.filter(email=new_email).exclude(id=user.id).exists():
      messages.error(request, 'Another user with this email already exists.')
      return render(request, 'students/edit_student.html', {'student': student})

    user.first_name = first_name
    user.last_name = last_name
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

    # 📸 Robust Photo Handling: Delete old, upload new, or clear
    delete_photo = request.POST.get('delete_photo') == 'true'
    new_photo = request.FILES.get('photo')

    if new_photo:
      if student.photo:
        try:
          student.photo.delete(save=False)
        except Exception:
          pass
      student.photo = new_photo
    elif delete_photo:
      if student.photo:
        try:
          student.photo.delete(save=False)
        except Exception:
          pass
      student.photo = ''

    student.save()

    messages.success(
        request, f'✏️ Student {user.get_full_name()} updated successfully!'
    )
    return redirect('student_list')

  return render(request, 'students/edit_student.html', {'student': student})


# ----------------------------------------------------
# 4. DELETE: Remove Student Profile & Account
# ----------------------------------------------------
@login_required
def delete_student(request, student_id):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied.')
    return redirect('student_list')

  student = get_object_or_404(
      StudentProfile.objects.select_related('user'), id=student_id
  )
  student.user.delete()

  messages.success(request, '🗑️ Student record deleted successfully!')
  return redirect('student_list')


# ----------------------------------------------------
# 5. UTILITIES: Bulk Add, Digital Pass, CSV Export
# ----------------------------------------------------
@login_required
def bulk_add_students(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied.')
    return redirect('student_list')

  if request.method == 'POST' and request.FILES.get('csv_file'):
    csv_file = request.FILES['csv_file']
    decoded_file = csv_file.read().decode('utf-8').splitlines()
    reader = csv.reader(decoded_file)
    next(reader, None)

    from accounts.models import User

    count = 0
    with transaction.atomic():
      for row in reader:
        if len(row) >= 7:
          first_name, last_name, email, course, year, division, roll_number = [
              x.strip() for x in row[:7]
          ]

          if not User.objects.filter(username=email).exists():
            random_password = generate_student_password()

            user = User.objects.create_user(
                username=email,
                email=email,
                password=random_password,
                first_name=first_name,
                last_name=last_name,
            )
            student = StudentProfile.objects.create(
                user=user,
                course=course,
                year=year,
                division=division,
                roll_number=roll_number,
            )

            # QR Code Generation
            try:
              qr_text = f'STUDENT_PASS:{student.student_id}'
              qr_img = qrcode.make(qr_text)
              buffer = io.BytesIO()
              qr_img.save(buffer, format='PNG')
              qr_b64 = base64.b64encode(buffer.getvalue()).decode()
              student.qr_code = f'data:image/png;base64,{qr_b64}'
              student.save(update_fields=['qr_code'])
            except Exception:
              pass

            # Async Credentials Email
            email_content = f"""Dear {first_name} {last_name},

Welcome to Vishwabharti Mahavidyalaya Enterprise Portal!

Your student login credentials:
Student ID : {student.student_id}
Username   : {email}
Password   : {random_password}
Course     : {course} ({year})

Login URL: https://cem-live-w7jl.vercel.app/accounts/login/
"""
            send_mail_async(
                'Vishwabharti Portal - Student Credentials',
                email_content,
                [email],
            )
            count += 1

    messages.success(
        request,
        f'🎉 Successfully uploaded {count} students with unique credentials!',
    )
    return redirect('student_list')

  return render(request, 'students/bulk_add.html')


@login_required
def student_pass(request, student_id):
  student = get_object_or_404(StudentProfile, id=student_id)

  qr_content = f'STUDENT_PASS:{student.student_id}'
  qr = qrcode.QRCode(version=1, box_size=8, border=2)
  qr.add_data(qr_content)
  qr.make(fit=True)

  img = qr.make_image(fill_color='#5C061C', back_color='white')
  buffer = io.BytesIO()
  img.save(buffer, format='PNG')
  qr_b64 = base64.b64encode(buffer.getvalue()).decode()

  context = {
      'student': student,
      'qr_b64': qr_b64,
  }
  return render(request, 'students/id_card.html', context)


@login_required
def export_students_excel(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied.')
    return redirect('student_list')

  response = HttpResponse(content_type='text/csv')
  response['Content-Disposition'] = (
      'attachment; filename="students_directory.csv"'
  )

  writer = csv.writer(response)
  writer.writerow([
      'Student ID',
      'First Name',
      'Last Name',
      'Email',
      'Department',
      'Course',
      'Year',
      'Division',
      'Roll Number',
  ])

  # ⚡ Chunked streaming with iterator() for low memory consumption
  for student in (
      StudentProfile.objects.select_related('user').all().iterator(chunk_size=500)
  ):
    writer.writerow([
        student.student_id,
        student.user.first_name,
        student.user.last_name,
        student.user.email,
        student.department,
        student.course,
        student.year,
        student.division,
        student.roll_number,
    ])

  return response


# ----------------------------------------------------
# 6. STUDENT SELF-SERVICE: Profile View & Edit (With Photo Deletion)
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

    # 📸 Photo Upload / Deletion logic for student self-service
    delete_photo = request.POST.get('delete_photo') == 'true'
    new_photo = request.FILES.get('photo')

    if new_photo:
      if student.photo:
        try:
          student.photo.delete(save=False)
        except Exception:
          pass
      student.photo = new_photo
    elif delete_photo:
      if student.photo:
        try:
          student.photo.delete(save=False)
        except Exception:
          pass
      student.photo = ''

    student.save()

    messages.success(request, '🎉 Profile updated successfully!')
    return redirect('student_profile_view')

  return render(request, 'students/edit_my_profile.html', {'student': student})


# ----------------------------------------------------
# 7. ADMIN MANAGEMENT: Add Banner & Announcement
# ----------------------------------------------------
@login_required
def add_banner(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied. Admin permissions required.')
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
          image=image,
      )
      messages.success(request, '🎉 Banner image uploaded successfully!')
      return redirect('student_dashboard')
    else:
      messages.error(request, 'Please provide a Title and Banner Image.')

  return render(request, 'students/add_banner.html')


@login_required
def add_announcement(request):
  if not is_admin_user(request.user):
    messages.error(request, 'Access denied. Admin permissions required.')
    return redirect('student_dashboard')

  if request.method == 'POST':
    notice_text = request.POST.get('notice_text', '').strip() or request.POST.get(
        'title', ''
    ).strip()

    if notice_text:
      AnnouncementNotice.objects.create(notice_text=notice_text, is_active=True)
      messages.success(
          request, '📢 Announcement posted! It will remain active for 24 hours.'
      )
      return redirect('student_dashboard')
    else:
      messages.error(request, 'Notice text cannot be empty.')

  return render(request, 'students/add_announcement.html')


# ----------------------------------------------------
# 8. STUDENT HOME PAGE / DASHBOARD (Optimized Queries)
# ----------------------------------------------------
@login_required
def student_dashboard(request):
  if is_admin_user(request.user):
    return redirect('student_list')

  student = get_object_or_404(StudentProfile, user=request.user)

  banners = BannerImage.objects.filter(is_active=True).order_by('-created_at')[
      :5
  ]

  last_24_hours = timezone.now() - timedelta(hours=24)
  latest_notice = (
      AnnouncementNotice.objects.filter(
          is_active=True, created_at__gte=last_24_hours
      )
      .order_by('-created_at')
      .first()
  )

  registered_events = EventRegistration.objects.filter(
      student=student
  ).select_related('event')[:5]
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