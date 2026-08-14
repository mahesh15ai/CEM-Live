from django.urls import path
from . import views

urlpatterns = [
    # 📌 १. तुमचा आधीचा Event/General Scanner रूट (Existing)
    path('scan/', views.scan_attendance, name='scan_attendance'),

    # 📌 २. नवीन Class Teacher Attendance Hub (Dual: QR + Manual)
    path('class/', views.class_attendance_dashboard, name='class_attendance_dashboard'),
    path('class/submit-manual/', views.submit_manual_attendance, name='submit_manual_attendance'),
    path('class/scan-qr-api/', views.scan_qr_attendance, name='scan_qr_attendance'),
    
    # 📌 ३. Monthly & Yearly Reports & CSV Export
    path('class/report/', views.monthly_yearly_report, name='monthly_yearly_report'),
    path('class/export-csv/', views.export_attendance_csv, name='export_attendance_csv'),
]