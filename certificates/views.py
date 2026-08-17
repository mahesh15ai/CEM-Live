import base64
import io
import threading
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from students.models import StudentProfile
from .models import Certificate


# ----------------------------------------------------
# Helper: Background Email Dispatch
# ----------------------------------------------------
def send_cert_notification_async(student_name, student_email, cert_title, cert_id):
    def _send():
        subject = f"🎓 Certificate Issued: {cert_title} - Vishwabharti Mahavidyalaya"
        content = f"""Dear {student_name},

Congratulations!

Your certificate for '{cert_title}' has been successfully issued.

Certificate ID : {cert_id}

You can view and download your verified digital certificate here:
https://cem-live-w7jl.vercel.app/certificates/view/{cert_id}/

Best Regards,
Vishwabharti Mahavidyalaya, CIDCO, Nanded
"""
        try:
            send_mail(
                subject=subject,
                message=content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student_email],
                fail_silently=True,
            )
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def is_admin_or_staff(user):
    return user.is_superuser or user.is_staff or getattr(user, 'is_admin', False)


# ----------------------------------------------------
# 1. READ: Certificate Directory (Paginated & Searchable)
# ----------------------------------------------------
@login_required
def certificate_list(request):
    user = request.user
    is_admin = is_admin_or_staff(user)
    search_query = request.GET.get('search', '').strip()

    if is_admin:
        certs_qs = Certificate.objects.select_related('student__user').all().order_by('-issue_date')
    else:
        if hasattr(user, 'student_profile'):
            certs_qs = Certificate.objects.filter(student=user.student_profile).select_related('student__user').order_by('-issue_date')
        else:
            certs_qs = Certificate.objects.none()

    if search_query:
        certs_qs = certs_qs.filter(
            Q(title__icontains=search_query)
            | Q(certificate_id__icontains=search_query)
            | Q(student__student_id__icontains=search_query)
            | Q(student__user__first_name__icontains=search_query)
            | Q(student__user__last_name__icontains=search_query)
        )

    # ⚡ Paginate: 20 certificates per page
    paginator = Paginator(certs_qs, 20)
    page_number = request.GET.get('page')

    try:
        certificates = paginator.page(page_number)
    except PageNotAnInteger:
        certificates = paginator.page(1)
    except EmptyPage:
        certificates = paginator.page(paginator.num_pages)

    context = {
        'certificates': certificates,
        'is_admin': is_admin,
        'search_query': search_query,
    }
    return render(request, 'certificates/certificate_list.html', context)


# ----------------------------------------------------
# 2. CREATE: Issue New Certificate (With Async Email)
# ----------------------------------------------------
@login_required
def issue_certificate(request):
    if not is_admin_or_staff(request.user):
        messages.error(request, "Access denied. Admin permissions required.")
        return redirect('certificate_list')

    students = StudentProfile.objects.select_related('user').all().order_by('user__first_name')

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        title = request.POST.get('title', '').strip()
        certificate_type = request.POST.get('certificate_type', 'Participation').strip()
        description = request.POST.get('description', '').strip()

        student = get_object_or_404(StudentProfile.objects.select_related('user'), id=student_id)

        with transaction.atomic():
            cert = Certificate.objects.create(
                student=student,
                title=title,
                certificate_type=certificate_type,
                description=description,
            )

        cert_id_val = getattr(cert, 'certificate_id', str(cert.id))

        # Non-blocking async email delivery
        send_cert_notification_async(
            student_name=student.user.get_full_name(),
            student_email=student.user.email,
            cert_title=title,
            cert_id=cert_id_val,
        )

        messages.success(
            request,
            f"🎓 Certificate issued successfully to {student.user.get_full_name()}! ID: {cert_id_val}"
        )
        return redirect('certificate_list')

    return render(request, 'certificates/issue_certificate.html', {'students': students})


# ----------------------------------------------------
# 3. VIEW: HTML Certificate Display with QR Code
# ----------------------------------------------------
@login_required
def view_certificate(request, certificate_id):
    cert = get_object_or_404(
        Certificate.objects.select_related('student__user'),
        certificate_id=certificate_id
    )

    # Verification QR Code
    qr_content = f"https://cem-live-w7jl.vercel.app/certificates/verify/{cert.certificate_id}/"
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#5C061C", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    context = {
        'cert': cert,
        'qr_b64': qr_b64,
    }
    return render(request, 'certificates/view_certificate.html', context)


# ----------------------------------------------------
# 4. DOWNLOAD: In-Memory Fast Vector PDF Generator
# ----------------------------------------------------
@login_required
def download_certificate_pdf(request, certificate_id):
    cert = get_object_or_404(
        Certificate.objects.select_related('student__user'),
        certificate_id=certificate_id
    )

    # Security check: Admins or the certificate owner can download
    if not is_admin_or_staff(request.user):
        if not hasattr(request.user, 'student_profile') or cert.student != request.user.student_profile:
            messages.error(request, "Access denied.")
            return redirect('certificate_list')

    student = cert.student

    # In-memory byte buffer (No disk writes)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Outer Crimson Border
    p.setStrokeColor(colors.HexColor('#5C061C'))
    p.setLineWidth(5)
    p.rect(20, 20, width - 40, height - 40)

    # Inner Gold Accent Border
    p.setStrokeColor(colors.HexColor('#D4AF37'))
    p.setLineWidth(1.5)
    p.rect(26, 26, width - 52, height - 52)

    # Header
    p.setFont("Helvetica-Bold", 24)
    p.setFillColor(colors.HexColor('#5C061C'))
    p.drawCentredString(width / 2.0, height - 75, "VISHWABHARTI MAHAVIDYALAYA")

    p.setFont("Helvetica", 11)
    p.setFillColor(colors.HexColor('#4A5568'))
    p.drawCentredString(width / 2.0, height - 95, "CIDCO, Nanded, Maharashtra | Affiliated to SRTMUN")

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(colors.HexColor('#1A202C'))
    p.drawCentredString(width / 2.0, height - 140, f"CERTIFICATE OF {cert.certificate_type.upper()}")

    # Body
    p.setFont("Helvetica", 13)
    p.setFillColor(colors.HexColor('#2D3748'))
    p.drawCentredString(width / 2.0, height - 180, "This is proudly presented to")

    p.setFont("Helvetica-Bold", 22)
    p.setFillColor(colors.HexColor('#5C061C'))
    p.drawCentredString(width / 2.0, height - 215, student.user.get_full_name().upper())

    p.setFont("Helvetica", 12)
    p.setFillColor(colors.HexColor('#4A5568'))
    details_line = f"Student ID: {student.student_id} | Class: {student.course} ({student.year})"
    p.drawCentredString(width / 2.0, height - 240, details_line)

    desc_line = f"for outstanding achievement in '{cert.title}'"
    p.drawCentredString(width / 2.0, height - 275, desc_line)

    if cert.description:
        p.setFont("Helvetica-Oblique", 11)
        p.drawCentredString(width / 2.0, height - 298, f"\"{cert.description[:90]}\"")

    date_str = cert.issue_date.strftime('%B %d, %Y') if cert.issue_date else "N/A"
    p.setFont("Helvetica", 11)
    p.drawCentredString(width / 2.0, height - 325, f"Date of Issue: {date_str}")

    # Embed Verification QR Code
    qr_content = f"https://cem-live-w7jl.vercel.app/certificates/verify/{cert.certificate_id}/"
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(qr_content)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#5C061C", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    p.drawImage(ImageReader(qr_buffer), 55, 45, width=65, height=65)

    # Verification String & Signatures
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.HexColor('#718096'))
    p.drawString(55, 35, f"ID: {cert.certificate_id}")

    p.setStrokeColor(colors.HexColor('#A0AEC0'))
    p.setLineWidth(1)
    p.line(width - 230, 70, width - 55, 70)

    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.HexColor('#1A202C'))
    p.drawCentredString(width - 142, 55, "Authorized Signatory")
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.HexColor('#718096'))
    p.drawCentredString(width - 142, 42, "Principal / Event Authority")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{cert.certificate_id}.pdf"'
    return response


# ----------------------------------------------------
# 5. PUBLIC: Verify Certificate Endpoint (No Login Required)
# ----------------------------------------------------
def verify_certificate(request, certificate_id):
    cert = get_object_or_404(
        Certificate.objects.select_related('student__user'),
        certificate_id=certificate_id
    )
    return render(request, 'certificates/verify_certificate.html', {'cert': cert})