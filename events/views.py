import base64
import io
import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from students.models import StudentProfile
from .models import Event, EventAttendance, EventRegistration


def is_admin_or_staff(user):
  return user.is_superuser or user.is_staff or getattr(user, 'is_admin', False)


# ----------------------------------------------------
# 1. READ: Event List & Directory (Paginated & Searchable)
# ----------------------------------------------------
@login_required
def event_list(request):
  search_query = request.GET.get('search', '').strip()

  events_qs = Event.objects.all().order_by('-event_date', '-event_time')

  if search_query:
    events_qs = events_qs.filter(
        Q(title__icontains=search_query)
        | Q(description__icontains=search_query)
        | Q(venue__icontains=search_query)
    )

  # Efficient O(1) set lookup for student registrations
  user_registered_event_ids = set()
  if hasattr(request.user, 'student_profile'):
    user_registered_event_ids = set(
        EventRegistration.objects.filter(
            student=request.user.student_profile
        ).values_list('event_id', flat=True)
    )

  # ⚡ Paginate: 9 events per page
  paginator = Paginator(events_qs, 9)
  page_number = request.GET.get('page')

  try:
    events = paginator.page(page_number)
  except PageNotAnInteger:
    events = paginator.page(1)
  except EmptyPage:
    events = paginator.page(paginator.num_pages)

  context = {
      'events': events,
      'registered_event_ids': user_registered_event_ids,
      'search_query': search_query,
      'is_admin': is_admin_or_staff(request.user),
  }
  return render(request, 'events/event_list.html', context)


# ----------------------------------------------------
# 2. CREATE: Publish Event (Admin / Staff Only)
# ----------------------------------------------------
@login_required
def create_event(request):
  if not is_admin_or_staff(request.user):
    messages.error(request, 'Access denied. Admin permissions required.')
    return redirect('event_list')

  if request.method == 'POST':
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    event_date = request.POST.get('event_date')
    event_time = request.POST.get('event_time')
    venue = request.POST.get('venue', '').strip()
    poster = request.FILES.get('poster')

    if not title or not event_date:
      messages.error(request, 'Please provide at least a title and event date.')
      return render(request, 'events/create_event.html')

    Event.objects.create(
        title=title,
        description=description,
        event_date=event_date,
        event_time=event_time,
        venue=venue,
        poster=poster,
    )
    messages.success(request, f"🎉 Event '{title}' published successfully!")
    return redirect('event_list')

  return render(request, 'events/create_event.html')


# ----------------------------------------------------
# 3. REGISTRATION: Register Student for Event
# ----------------------------------------------------
@login_required
def register_event(request, event_id):
  if not hasattr(request.user, 'student_profile'):
    messages.error(request, 'Only students can register for events.')
    return redirect('event_list')

  event = get_object_or_404(Event, id=event_id)
  student = request.user.student_profile

  registration, created = EventRegistration.objects.get_or_create(
      event=event, student=student
  )

  if created:
    messages.success(request, f'✅ Successfully registered for {event.title}!')
  else:
    messages.warning(
        request, f'⚠️ You are already registered for {event.title}.'
    )

  return redirect('event_list')


# ----------------------------------------------------
# 4. PASS: Generate Student Event QR Entry Pass
# ----------------------------------------------------
@login_required
def event_pass(request, event_id):
  if not hasattr(request.user, 'student_profile'):
    messages.error(request, 'Only students can view event entry passes.')
    return redirect('event_list')

  event = get_object_or_404(Event, id=event_id)
  student = request.user.student_profile
  registration = get_object_or_404(
      EventRegistration, event=event, student=student
  )

  # QR format: EVENT_PASS:<event_id>:<student_id>
  qr_content = f'EVENT_PASS:{event.id}:{student.student_id}'
  qr = qrcode.QRCode(version=1, box_size=8, border=2)
  qr.add_data(qr_content)
  qr.make(fit=True)

  img = qr.make_image(fill_color='#5C061C', back_color='white')
  buffer = io.BytesIO()
  img.save(buffer, format='PNG')
  qr_b64 = base64.b64encode(buffer.getvalue()).decode()

  context = {
      'event': event,
      'student': student,
      'registration': registration,
      'qr_b64': qr_b64,
  }
  return render(request, 'events/event_pass.html', context)


# ----------------------------------------------------
# 5. SCANNER: Live Scanner UI
# ----------------------------------------------------
@login_required
def scan_event_pass(request, event_id):
  if not is_admin_or_staff(request.user):
    messages.error(request, 'Access denied. Admin/Staff permission required.')
    return redirect('event_list')

  event = get_object_or_404(Event, id=event_id)
  recent_attendances = (
      EventAttendance.objects.filter(event=event)
      .select_related('student__user')
      .order_by('-entry_time')[:10]
  )

  return render(
      request,
      'events/scan_event_pass.html',
      {'event': event, 'recent_attendances': recent_attendances},
  )


# ----------------------------------------------------
# 6. SCANNER: Fast AJAX QR Verification Endpoint
# ----------------------------------------------------
@csrf_exempt
@login_required
def process_event_qr(request):
  if request.method == 'POST':
    qr_code = request.POST.get('qr_code', '').strip()

    # Check QR format: EVENT_PASS:<event_id>:<student_id>
    if not qr_code.startswith('EVENT_PASS:'):
      return JsonResponse(
          {'status': 'error', 'message': '❌ Invalid Event Pass QR Code!'}
      )

    parts = qr_code.split(':')
    if len(parts) != 3:
      return JsonResponse(
          {'status': 'error', 'message': '❌ Corrupted Pass QR Data!'}
      )

    event_id, student_id = parts[1], parts[2]

    event = Event.objects.filter(id=event_id).first()
    student = (
        StudentProfile.objects.select_related('user')
        .filter(student_id=student_id)
        .first()
    )

    if not event or not student:
      return JsonResponse({
          'status': 'error',
          'message': '❌ Event or Student Profile not found!',
      })

    # Check if student is registered
    is_registered = EventRegistration.objects.filter(
        event=event, student=student
    ).exists()
    if not is_registered:
      return JsonResponse({
          'status': 'error',
          'message': (
              f'⚠️ Student {student.user.get_full_name()}'
              f' ({student.student_id}) has NOT registered for this event!'
          ),
      })

    # Mark attendance with transaction safety
    with transaction.atomic():
      attendance, created = EventAttendance.objects.get_or_create(
          event=event, student=student
      )

    if created:
      return JsonResponse({
          'status': 'success',
          'message': (
              f'🎉 ENTRY GRANTED! Welcome {student.user.get_full_name()}'
              f' ({student.student_id})'
          ),
          'student_name': student.user.get_full_name(),
          'student_id': student.student_id,
          'course': student.course,
          'time': attendance.entry_time.strftime('%I:%M %p'),
      })
    else:
      return JsonResponse({
          'status': 'warning',
          'message': (
              f'⚠️ ALREADY ENTERED! {student.user.get_full_name()} checked in'
              f" earlier at {attendance.entry_time.strftime('%I:%M %p')}."
          ),
          'student_name': student.user.get_full_name(),
          'student_id': student.student_id,
      })

  return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


# ----------------------------------------------------
# 7. REPORTS: Attendance Records (Paginated)
# ----------------------------------------------------
@login_required
def event_attendance_records(request, event_id):
  if not is_admin_or_staff(request.user):
    messages.error(request, 'Access denied.')
    return redirect('event_list')

  event = get_object_or_404(Event, id=event_id)
  attendances_qs = (
      EventAttendance.objects.filter(event=event)
      .select_related('student__user')
      .order_by('-entry_time')
  )
  registrations_count = EventRegistration.objects.filter(event=event).count()

  # ⚡ Paginate: 25 attendance logs per page
  paginator = Paginator(attendances_qs, 25)
  page_number = request.GET.get('page')

  try:
    attendances = paginator.page(page_number)
  except PageNotAnInteger:
    attendances = paginator.page(1)
  except EmptyPage:
    attendances = paginator.page(paginator.num_pages)

  return render(
      request,
      'events/attendance_records.html',
      {
          'event': event,
          'attendances': attendances,
          'registrations_count': registrations_count,
      },
  )