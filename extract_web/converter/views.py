from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegistrationForm, AdminUserEditForm, AdminSetPasswordForm # 更新导入
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
import os
from django.contrib import messages # 新增导入

# Create your views here.

def index(request):
    # 未来这里会处理表单提交和文件上传
    return render(request, "converter/index.html")

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in directly after registration
            
            # Create user-specific directory
            try:
                user_dir = os.path.join(settings.BASE_DIR.parent, 'his_pic', user.username)
                os.makedirs(user_dir, exist_ok=True)
                # You might want to add some logging here if needed
            except OSError as e:
                # Handle or log the error if directory creation fails
                print(f"Error creating directory for user {user.username}: {e}")
                # Depending on policy, you might want to inform the user or take other actions
            
            return redirect('converter:index')  # Redirect to the main page
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

# Helper to check if user is superuser
def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def admin_console_index(request):
    return render(request, 'custom_admin/admin_index.html')

@login_required
@user_passes_test(is_superuser)
def admin_user_management(request):
    # Placeholder: Add logic for user CRUD operations here
    users = User.objects.all()
    return render(request, 'custom_admin/user_management.html', {'users': users})

@login_required
@user_passes_test(is_superuser)
def admin_file_management(request):
    # Placeholder: Add logic for file management here
    return render(request, 'custom_admin/file_management.html')

@login_required
@user_passes_test(is_superuser)
def admin_delete_user(request, user_id):
    if request.method == 'POST': # 最好使用 POST 请求进行删除操作
        user_to_delete = get_object_or_404(User, pk=user_id)
        if user_to_delete.is_superuser and not request.user.is_superuser: # 防止非超级管理员删除超级管理员
            messages.error(request, "您没有权限删除超级管理员用户。")
        elif user_to_delete == request.user: # 防止用户删除自己
            messages.error(request, "您不能删除您自己的账户。")
        else:
            username = user_to_delete.username
            # 在删除用户前，可能需要处理相关联的用户文件夹
            user_folder_path = os.path.join(settings.BASE_DIR.parent, 'his_pic', username)
            if os.path.exists(user_folder_path):
                try:
                    # 注意：shutil.rmtree 会删除整个文件夹及其内容，请谨慎使用
                    import shutil
                    shutil.rmtree(user_folder_path)
                    messages.success(request, f"用户 '{username}' 的文件夹已成功删除。")
                except OSError as e:
                    messages.error(request, f"删除用户 '{username}' 的文件夹时出错: {e}")
            
            user_to_delete.delete()
            messages.success(request, f"用户 '{username}' 已成功删除。")
    else:
        # 对于GET请求，可以显示一个确认页面，或者像这里一样直接重定向（不推荐用于生产环境的删除操作）
        messages.warning(request, "删除操作应通过POST请求执行。")
    
    return redirect('converter:admin_user_management')

@login_required
@user_passes_test(is_superuser)
def admin_edit_user(request, user_id):
    user_to_edit = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # 根据提交的表单类型分别处理
        if 'change_info' in request.POST:
            user_form = AdminUserEditForm(request.POST, instance=user_to_edit)
            password_form = AdminSetPasswordForm(user_to_edit) # 保持密码表单在上下文
            if user_form.is_valid():
                user_form.save()
                messages.success(request, f"用户 '{user_to_edit.username}' 的信息已更新。")
                return redirect('converter:admin_user_management')
        elif 'set_password' in request.POST:
            password_form = AdminSetPasswordForm(user_to_edit, request.POST)
            user_form = AdminUserEditForm(instance=user_to_edit) # 保持用户信息表单在上下文
            if password_form.is_valid():
                password_form.save()
                messages.success(request, f"用户 '{user_to_edit.username}' 的密码已重置。")
                return redirect('converter:admin_user_management')
        else:
            # 未知POST请求或缺少标识，可以简单地重新加载表单
            user_form = AdminUserEditForm(instance=user_to_edit)
            password_form = AdminSetPasswordForm(user_to_edit)
            messages.error(request, "无效的请求。")

    else:
        user_form = AdminUserEditForm(instance=user_to_edit)
        password_form = AdminSetPasswordForm(user_to_edit)
        
    return render(request, 'custom_admin/user_edit_form.html', {
        'user_form': user_form,
        'password_form': password_form,
        'user_to_edit': user_to_edit
    })
