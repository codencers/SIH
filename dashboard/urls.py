from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload_file'),
    path('download/<str:file_name>/', views.download_file, name='download_file'),
    path('delete/<str:file_name>/', views.delete_file, name='delete_file'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('signup/', views.signup_view, name='signup'),
]
