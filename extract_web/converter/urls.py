from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "converter"
urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("admin-console/", views.admin_console_index, name="admin_console_index"),
    path("admin-console/user-management/", views.admin_user_management, name="admin_user_management"),
    path("admin-console/file-management/", views.admin_file_management, name="admin_file_management"),
    path("admin-console/user/delete/<int:user_id>/", views.admin_delete_user, name="admin_delete_user"),
    path("admin/users/edit/<int:user_id>/", views.admin_edit_user, name="admin_edit_user"),
    
    # 新的API端点
    path("api/file-to-pdf/", views.file_to_pdf_view, name="api_file_to_pdf"),
    path("api/img-to-file/", views.img_to_file_view, name="api_img_to_file"),
    path("api/pdf-to-file/", views.pdf_to_file_view, name="api_pdf_to_file"),
    path("api/speech-to-text/", views.speech_to_text_view, name="api_speech_to_text"),

    # 旧的 process_images 端点 - 现在指向一个废弃提示视图
    # 客户端应更新为使用上述新的API端点。
    path("process-images/", views.process_images_view, name="process_images"),
    path("check_task_status/<str:task_id>/", views.check_task_status_view, name="check_task_status"),
    path("download_file/<str:request_id>/<str:filename>/", views.download_converted_file_view, name="download_file"),
    # path('api/analyze_document', views.analyze_document_view, name='analyze_document'),  # Example for a potential new API endpoint
    path("api/video-to-extraction/", views.process_video_extraction_view, name="api_video_to_extraction"), # ADDED for new video processing
    
    path("history/", views.conversion_history_view, name="conversion_history"),
    path("delete-converted-file/<str:date_str>/<str:filename>/", views.delete_converted_file_view, name="delete_converted_file"),
    path("history/delete_all_for_date/<str:date_str>/", views.delete_all_for_date_view, name="delete_all_for_date"),
    path('download/<str:username>/<str:date_str>/<str:filename>/', views.download_converted_file_view, name='download_converted_file'),
]

# The following line should be AFTER the urlpatterns list
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# This is typically done in the project's main urls.py for development server 