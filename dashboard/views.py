import os
import json
import google.generativeai as genai
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .supabase_client import get_supabase_client
import fitz  # PyMuPDF
from django.core.files.uploadedfile import UploadedFile

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)

def landing(request):
    """Landing page view"""
    return render(request, 'dashboard/landing.html')

def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'dashboard/login.html', {'form': form})

def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('landing')

@login_required
def dashboard(request):
    """Main dashboard showing files from Supabase"""
    try:
        supabase = get_supabase_client()
        bucket_name = settings.BUCKET_NAME
        
        # List files in bucket
        files_response = supabase.storage.from_(bucket_name).list()
        files = files_response if files_response else []
        
        # Filter out folders and get file details
        file_list = []
        for file_item in files:
            if file_item.get('name') and not file_item.get('name').endswith('/'):
                file_info = {
                    'name': file_item.get('name'),
                    'size': file_item.get('metadata', {}).get('size', 0),
                    'created_at': file_item.get('created_at'),
                    'updated_at': file_item.get('updated_at'),
                }
                file_list.append(file_info)
        
        return render(request, 'dashboard/dashboard.html', {
            'files': file_list,
            'bucket_name': bucket_name
        })
    
    except Exception as e:
        messages.error(request, f"Error loading files: {str(e)}")
        return render(request, 'dashboard/dashboard.html', {'files': []})

@login_required
def upload_file(request):
    """Handle file upload to Supabase"""
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            uploaded_file = request.FILES['file']
            supabase = get_supabase_client()
            bucket_name = settings.BUCKET_NAME
            
            # Read file content
            file_content = uploaded_file.read()
            
            # Upload to Supabase
            response = supabase.storage.from_(bucket_name).upload(
                uploaded_file.name, 
                file_content,
                file_options={"content-type": uploaded_file.content_type}
            )
            
            if response:
                messages.success(request, f"File '{uploaded_file.name}' uploaded successfully!")
            else:
                messages.error(request, "Upload failed. Please try again.")
                
        except Exception as e:
            messages.error(request, f"Upload error: {str(e)}")
    
    return redirect('dashboard')

@login_required
def download_file(request, file_name):
    """Handle file download from Supabase"""
    try:
        supabase = get_supabase_client()
        bucket_name = settings.BUCKET_NAME
        
        # Get public URL for the file
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return redirect(public_url)
        
    except Exception as e:
        messages.error(request, f"Download error: {str(e)}")
        return redirect('dashboard')

@login_required
def delete_file(request, file_name):
    """Handle file deletion from Supabase"""
    try:
        supabase = get_supabase_client()
        bucket_name = settings.BUCKET_NAME
        
        response = supabase.storage.from_(bucket_name).remove([file_name])
        if response:
            messages.success(request, f"File '{file_name}' deleted successfully!")
        else:
            messages.error(request, "Delete failed. Please try again.")
            
    except Exception as e:
        messages.error(request, f"Delete error: {str(e)}")
    
    return redirect('dashboard')


@login_required
def chatbot(request):
    response_text = ""
    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        pdf_file: UploadedFile = request.FILES.get("pdf_file", None)
        translate_to = request.POST.get("translate_to", "").strip()

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")

            if pdf_file and pdf_file.size > 0:
                # Read the PDF bytes fully BEFORE re-opening with fitz
                pdf_bytes = pdf_file.read()
                if not pdf_bytes:
                    response_text = "Uploaded PDF seems empty."
                else:
                    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    full_text = ""
                    for page in pdf_doc:
                        full_text += page.get_text()

                    if not full_text.strip():
                        response_text = "Could not extract any readable text from PDF."
                    else:
                        prompt = f"Please provide a concise summary for the following text:\n{full_text}"
                        summary_response = model.generate_content(prompt)
                        summary = summary_response.text

                        if translate_to:
                            translate_prompt = f"Translate the following text to {translate_to}:\n{summary}"
                            translation_response = model.generate_content(translate_prompt)
                            response_text = translation_response.text
                        else:
                            response_text = summary

            elif user_message:
                chat_response = model.generate_content(user_message)
                response_text = chat_response.text

            else:
                response_text = "Please enter a message or upload a PDF file."

        except Exception as e:
            response_text = f"Sorry, encountered error: {str(e)}"

    return render(request, "dashboard/chatbot.html", {"response": response_text})



from django.contrib.auth.forms import UserCreationForm

def signup_view(request):
    """User registration view"""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto login after signup
            messages.success(request, "Account created successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = UserCreationForm()
    return render(request, 'dashboard/signup.html', {'form': form})

@login_required
def download_file(request, file_name):
    """Redirects to public Supabase URL for downloading/viewing the file"""
    try:
        supabase = get_supabase_client()
        bucket_name = settings.BUCKET_NAME
        
        # Get the public URL for the file in the bucket
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        
        # Redirect user to the public file URL
        return redirect(public_url)
    
    except Exception as e:
        messages.error(request, f"Download error: {str(e)}")
        return redirect('dashboard')

