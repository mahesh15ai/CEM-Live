from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from students.models import StudentProfile
from teachers.models import TeacherProfile


def login_view(request):
    # जर आधीच लॉगिन असेल तर रोलनुसार योग्य पानावर पाठवा
    if request.user.is_authenticated:
        if getattr(request.user, 'is_teacher', False) or hasattr(request.user, 'teacher_profile'):
            return redirect('teacher_dashboard')
        elif request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin', False):
            return redirect('student_list')
        elif getattr(request.user, 'is_student', False) or hasattr(request.user, 'student_profile'):
            return redirect('student_dashboard')
        return redirect('student_list')

    if request.method == 'POST':
        input_identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        target_username = input_identifier

        # 1. Student ID जुळतोय का ते तपासा (उदा. VBM20260001)
        student_profile = StudentProfile.objects.filter(student_id__iexact=input_identifier).select_related('user').first()
        if student_profile and student_profile.user:
            target_username = student_profile.user.username
        else:
            # 2. Teacher ID जुळतोय का ते तपासा (उदा. VBM-T-001)
            teacher_profile = TeacherProfile.objects.filter(teacher_id__iexact=input_identifier).select_related('user').first()
            if teacher_profile and teacher_profile.user:
                target_username = teacher_profile.user.username
            else:
                # 3. Email ID जुळतोय का ते तपासा
                user_by_email = User.objects.filter(email__iexact=input_identifier).first()
                if user_by_email:
                    target_username = user_by_email.username

        # Authenticate User
        user = authenticate(request, username=target_username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")

                # 📌 Role-Based Clean Redirect (Priority-wise):
                
                # १. जर Teacher असेल तर Teacher Dashboard वर पाठवा
                if getattr(user, 'is_teacher', False) or hasattr(user, 'teacher_profile'):
                    return redirect('teacher_dashboard')
                
                # २. जर Superuser / Admin असेल तर Student List वर पाठवा
                elif user.is_superuser or user.is_staff or getattr(user, 'is_admin', False):
                    return redirect('student_list')
                
                # ३. जर Student असेल तर Student Dashboard वर पाठवा
                elif getattr(user, 'is_student', False) or hasattr(user, 'student_profile'):
                    return redirect('student_dashboard')
                
                return redirect('student_list')
            else:
                messages.error(request, "This account has been disabled.")
        else:
            messages.error(request, "Invalid username, Email, ID or password.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')


def qr_login_view(request):
    if request.method == 'POST':
        qr_data = request.POST.get('qr_data', '').strip()
        
        # Clean QR prefixes
        student_id = qr_data.replace('STUDENT_PASS:', '').replace('STUDENT:', '').strip()

        student = StudentProfile.objects.filter(student_id__iexact=student_id).select_related('user').first()

        if student and student.user:
            user = student.user
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            
            login(request, user)
            messages.success(request, f"🎉 Welcome back, {user.first_name or user.username}! Logged in via Identity QR.")
            return redirect('student_dashboard')
        else:
            messages.error(request, f"❌ Invalid QR Pass. Scanned ID '{student_id}' does not match any student record.")
            return redirect('qr_login')

    return render(request, 'accounts/qr_login.html')


@login_required
def dashboard_redirect(request):
    """
    Directs the user to their designated portal based on their assigned role.
    """
    user = request.user
    
    if getattr(user, 'is_teacher', False) or hasattr(user, 'teacher_profile'):
        return redirect('teacher_dashboard')
        
    if user.is_superuser or user.is_staff or getattr(user, 'is_admin', False):
        return redirect('student_list')
    
    if getattr(user, 'is_student', False) or hasattr(user, 'student_profile'):
        return redirect('student_dashboard')
        
    return redirect('login')