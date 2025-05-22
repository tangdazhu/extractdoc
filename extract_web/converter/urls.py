from django.urls import path
from . import views

app_name = "converter"
urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("admin-console/", views.admin_console_index, name="admin_console_index"),
    path("admin-console/user-management/", views.admin_user_management, name="admin_user_management"),
    path("admin-console/file-management/", views.admin_file_management, name="admin_file_management"),
    path("admin-console/user/delete/<int:user_id>/", views.admin_delete_user, name="admin_delete_user"),
    path("admin-console/user/edit/<int:user_id>/", views.admin_edit_user, name="admin_edit_user"),
] 