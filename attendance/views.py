import csv
from datetime import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from students.models import StudentProfile
from teachers.models import TeacherProfile
from .models import AttendanceRecord, DailyClassAttendance


def is_admin_or_staff(user):
  return user.is_superuser or user.is_staff or getattr(user, 'is_admin', False)


# ----------------------------------------------------
# 📌 1. Event / Gate Scanner View (Single Scan per Day)
# ----------------------------------------------------
@login_required
def scan_attendance(request):
  if not is_admin_or_staff(request.user):
    messages.error(request, 'Access denied. Admin privileges required.')
    return redirect('event_list')

  if request.method == 'POST':
    qr_code_data = request.POST.get('qr_code_data', '').strip()
    student_id = (
        qr_code_data.replace('STUDENT_PASS:', '')
        .replace('STUDENT:', '')
        .strip()
    )

    student = (
        StudentProfile.objects.filter(student_id__iexact=student_id)
        .select_related('user')
        .first()
    )
    if not student:
      return JsonResponse(
          {'status': 'error', 'message': f'Student ID {student_id} not found.'},
          status=404,
      )

    today = timezone.now().date()
    marker_name = request.user.get_full_name() or request.user.username

    with transaction.atomic():
      record, created = AttendanceRecord.objects.get_or_create(
          student=student,
          date=today,
          defaults={
              'status': 'Present',
              'marked_by': marker_name,
          },
      )

    if not created:
      return JsonResponse({
          'status': 'warning',
          'message': (
              f'⚠️ Attendance already marked for {student.user.get_full_name()}'
              ' today.'
          ),
      })

    return JsonResponse({
        'status': 'success',
        'message': (
            f'✅ Attendance recorded: {student.user.get_full_name()}'
            f' ({student.student_id})'
        ),
    })

  today_records = (
      AttendanceRecord.objects.filter(date=timezone.now().date())
      .select_related('student__user')
      .order_by('-id')[:50]
  )
  return render(
      request, 'attendance/scanner.html', {'today_records': today_records}
  )


# ----------------------------------------------------
# 📌 2. Class Attendance Hub (Teacher UI)
# ----------------------------------------------------
@login_required
def class_attendance_dashboard(request):
  teacher = getattr(request.user, 'teacher_profile', None)
  is_admin = is_admin_or_staff(request.user)

  if not teacher and not is_admin:
    messages.error(
        request,
        'Access denied. Only Class Teachers and Admins can access attendance.',
    )
    return redirect('student_dashboard')

  today = timezone.now().date()

  course = (
      teacher.assigned_course
      if teacher and teacher.assigned_course
      else request.GET.get('course', 'BCA')
  )
  year = (
      teacher.assigned_year
      if teacher and teacher.assigned_year
      else request.GET.get('year', 'First Year')
  )
  division = (
      teacher.assigned_division
      if teacher and teacher.assigned_division
      else request.GET.get('division', 'A')
  )

  # Fetch all students in course/year/div
  students = (
      StudentProfile.objects.filter(
          course=course, year=year, division=division
      )
      .select_related('user')
      .order_by('roll_number')
  )

  # Map today's attendance status in 1 single query
  today_records = DailyClassAttendance.objects.filter(
      student__in=students, date=today
  ).values('student_id', 'status')

  attendance_map = {rec['student_id']: rec['status'] for rec in today_records}
  present_count = sum(
      1 for status in attendance_map.values() if status == 'Present'
  )

  context = {
      'teacher': teacher,
      'course': course,
      'year': year,
      'division': division,
      'today': today,
      'students': students,
      'attendance_map': attendance_map,
      'total_students': len(students),
      'present_count': present_count,
  }
  return render(
      request, 'attendance/class_attendance_dashboard.html', context
  )


# ----------------------------------------------------
# 📌 3. Manual Attendance Submit (Atomic Batch Optimization)
# ----------------------------------------------------
@login_required
def submit_manual_attendance(request):
  if request.method == 'POST':
    date_str = request.POST.get('attendance_date')
    attendance_date = (
        datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_str
        else timezone.now().date()
    )

    course = request.POST.get('course')
    year = request.POST.get('year')
    division = request.POST.get('division')

    students = StudentProfile.objects.filter(
        course=course, year=year, division=division
    )

    # ⚡ Batch transaction processing
    with transaction.atomic():
      for student in students:
        status_val = request.POST.get(f'status_{student.id}', 'Absent')
        DailyClassAttendance.objects.update_or_create(
            student=student,
            date=attendance_date,
            defaults={
                'status': status_val,
                'marked_by': request.user,
                'method': 'MANUAL',
            },
        )

    messages.success(
        request,
        f"Attendance for {attendance_date.strftime('%d-%b-%Y')} saved"
        ' successfully!',
    )
    return redirect('class_attendance_dashboard')

  return redirect('class_attendance_dashboard')


# ----------------------------------------------------
# 📌 4. Live Class QR Scanner API (Atomic Speed)
# ----------------------------------------------------
@csrf_exempt
@login_required
def scan_qr_attendance(request):
  if request.method != 'POST':
    return JsonResponse(
        {'status': 'error', 'message': 'Invalid request method.'}, status=405
    )

  try:
    data = json.loads(request.body)
    qr_content = data.get('qr_content', '').strip()

    if not qr_content:
      return JsonResponse(
          {'status': 'error', 'message': 'Empty QR content received.'},
          status=400,
      )

    student_id = (
        qr_content.replace('STUDENT_PASS:', '')
        .replace('STUDENT:', '')
        .strip()
    )

    student = (
        StudentProfile.objects.filter(student_id__iexact=student_id)
        .select_related('user')
        .first()
    )
    if not student:
      return JsonResponse(
          {'status': 'error', 'message': f"Student ID '{student_id}' not found."},
          status=404,
      )

    today = timezone.now().date()
    current_time_str = timezone.localtime().strftime('%I:%M %p')

    # Atomic Update or Create
    with transaction.atomic():
      record, created = DailyClassAttendance.objects.get_or_create(
          student=student,
          date=today,
          defaults={
              'status': 'Present',
              'marked_by': request.user,
              'method': 'QR_SCAN',
          },
      )

      if not created:
        if record.status == 'Present':
          return JsonResponse({
              'status': 'error',
              'message': (
                  f'⚠️ {student.user.get_full_name()} ({student.student_id}) is'
                  ' ALREADY marked Present today!'
              ),
          })
        else:
          # If previously marked Absent manually, update to Present
          record.status = 'Present'
          record.method = 'QR_SCAN'
          record.marked_by = request.user
          record.save(update_fields=['status', 'method', 'marked_by'])

    return JsonResponse({
        'status': 'success',
        'message': (
            f'Marked Present: {student.user.get_full_name()} (Roll No:'
            f" {student.roll_number or '-'})"
        ),
        'student_name': (
            student.user.get_full_name() or student.user.username
        ),
        'student_id': student.student_id,
        'time': current_time_str,
    })

  except Exception as e:
    return JsonResponse(
        {'status': 'error', 'message': f'Error: {e!s}'}, status=400
    )


# ----------------------------------------------------
# 📌 5. Monthly & Yearly Analytics Report (1 Single DB Query!)
# ----------------------------------------------------
@login_required
def monthly_yearly_report(request):
  teacher = getattr(request.user, 'teacher_profile', None)
  course = (
      teacher.assigned_course
      if teacher and teacher.assigned_course
      else request.GET.get('course', 'BCA')
  )
  year = (
      teacher.assigned_year
      if teacher and teacher.assigned_year
      else request.GET.get('year', 'First Year')
  )
  division = (
      teacher.assigned_division
      if teacher and teacher.assigned_division
      else request.GET.get('division', 'A')
  )

  current_year = int(request.GET.get('report_year', timezone.now().year))
  current_month = int(request.GET.get('report_month', timezone.now().month))

  # Distinct class active days
  total_month_days = (
      DailyClassAttendance.objects.filter(
          student__course=course,
          student__year=year,
          student__division=division,
          date__year=current_year,
          date__month=current_month,
      )
      .values('date')
      .distinct()
      .count()
  )

  total_year_days = (
      DailyClassAttendance.objects.filter(
          student__course=course,
          student__year=year,
          student__division=division,
          date__year=current_year,
      )
      .values('date')
      .distinct()
      .count()
  )

  # ⚡ Aggregated in ONE single query for all students (Replaces 160+ queries)
  students_with_stats = (
      StudentProfile.objects.filter(
          course=course, year=year, division=division
      )
      .select_related('user')
      .annotate(
          month_present=Count(
              Case(
                  When(
                      dailyclassattendance__date__year=current_year,
                      dailyclassattendance__date__month=current_month,
                      dailyclassattendance__status='Present',
                      then=1,
                  ),
                  output_field=IntegerField(),
              )
          ),
          year_present=Count(
              Case(
                  When(
                      dailyclassattendance__date__year=current_year,
                      dailyclassattendance__status='Present',
                      then=1,
                  ),
                  output_field=IntegerField(),
              )
          ),
      )
      .order_by('roll_number')
  )

  report_data = []
  for s in students_with_stats:
    month_pct = (
        round((s.month_present / total_month_days * 100), 1)
        if total_month_days > 0
        else 0.0
    )
    year_pct = (
        round((s.year_present / total_year_days * 100), 1)
        if total_year_days > 0
        else 0.0
    )

    report_data.append({
        'student': s,
        'month_present': s.month_present,
        'month_pct': month_pct,
        'year_present': s.year_present,
        'year_pct': year_pct,
    })

  context = {
      'report_data': report_data,
      'course': course,
      'year': year,
      'division': division,
      'current_month': current_month,
      'current_year': current_year,
      'total_month_days': total_month_days,
      'total_year_days': total_year_days,
  }
  return render(request, 'attendance/attendance_report.html', context)


# ----------------------------------------------------
# 📌 6. Export Report to CSV (Memory-Efficient Query)
# ----------------------------------------------------
@login_required
def export_attendance_csv(request):
  course = request.GET.get('course', 'BCA')
  year = request.GET.get('year', 'First Year')
  division = request.GET.get('division', 'A')
  current_year = int(request.GET.get('report_year', timezone.now().year))
  current_month = int(request.GET.get('report_month', timezone.now().month))

  response = HttpResponse(content_type='text/csv')
  response['Content-Disposition'] = (
      f'attachment; filename="attendance_{course}_{year}_{current_month}_{current_year}.csv"'
  )

  writer = csv.writer(response)
  writer.writerow([
      'Student ID',
      'Name',
      'Roll No',
      'Course',
      'Year',
      'Div',
      'Month Present Days',
      'Monthly %',
      'Yearly %',
  ])

  total_month_days = (
      DailyClassAttendance.objects.filter(
          student__course=course,
          student__year=year,
          student__division=division,
          date__year=current_year,
          date__month=current_month,
      )
      .values('date')
      .distinct()
      .count()
  )

  total_year_days = (
      DailyClassAttendance.objects.filter(
          student__course=course,
          student__year=year,
          student__division=division,
          date__year=current_year,
      )
      .values('date')
      .distinct()
      .count()
  )

  # Single annotated query
  students_with_stats = (
      StudentProfile.objects.filter(
          course=course, year=year, division=division
      )
      .select_related('user')
      .annotate(
          month_present=Count(
              Case(
                  When(
                      dailyclassattendance__date__year=current_year,
                      dailyclassattendance__date__month=current_month,
                      dailyclassattendance__status='Present',
                      then=1,
                  ),
                  output_field=IntegerField(),
              )
          ),
          year_present=Count(
              Case(
                  When(
                      dailyclassattendance__date__year=current_year,
                      dailyclassattendance__status='Present',
                      then=1,
                  ),
                  output_field=IntegerField(),
              )
          ),
      )
      .order_by('roll_number')
  )

  for s in students_with_stats:
    m_pct = (
        round((s.month_present / total_month_days * 100), 1)
        if total_month_days > 0
        else 0.0
    )
    y_pct = (
        round((s.year_present / total_year_days * 100), 1)
        if total_year_days > 0
        else 0.0
    )

    writer.writerow([
        s.student_id,
        s.user.get_full_name(),
        s.roll_number,
        s.course,
        s.year,
        s.division,
        s.month_present,
        f'{m_pct}%',
        f'{y_pct}%',
    ])

  return response