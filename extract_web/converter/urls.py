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
    path("process-images/", views.process_images_view, name="process_images"),
    path("history/", views.conversion_history_view, name="conversion_history"),
    path("delete-converted-file/<str:date_str>/<str:filename>/", views.delete_converted_file_view, name="delete_converted_file"),
]

# The following line should be AFTER the urlpatterns list
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# This is typically done in the project's main urls.py for development server 