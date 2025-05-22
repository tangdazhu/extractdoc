from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import User
import re

class RegistrationForm(UserCreationForm):
    username = forms.CharField(
        label='用户名',
        max_length=10,
        help_text='必填。10 个字符或更少。仅限字母和数字。',
        widget=forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 35ch;'})
    )
    # 密码字段将由 UserCreationForm 提供，并在 __init__ 中进行自定义

    class Meta(UserCreationForm.Meta): # 继承父类的 Meta 以获取 model = User 等设置
        fields = ('username',) # 只列出我们在类级别重新定义的字段
                                # UserCreationForm 会自动处理其 password 和 password2 字段

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # 调用父类的 __init__，它会设置好 password 和 password2 字段
        
        # 现在 self.fields['password'] 和 self.fields['password2'] 是由 UserCreationForm 设置的
        # 我们可以安全地修改它们
        if 'password' in self.fields: # UserCreationForm 内部称第一个密码字段为 'password'
            self.fields['password'].label = '密码'
            self.fields['password'].help_text = '密码必须是字母和数字的组合，不超过10位字符，且不能少于8位。'
            self.fields['password'].widget.attrs.update({'class': 'form-control', 'style': 'width: 35ch;'})
        
        if 'password2' in self.fields:
            self.fields['password2'].label = '确认密码'
            self.fields['password2'].help_text = '请再次输入您的密码进行确认。'
            self.fields['password2'].widget.attrs.update({'class': 'form-control', 'style': 'width: 35ch;'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            raise forms.ValidationError("用户名必须仅包含字母和数字。")
        if len(username) > 10:
            raise forms.ValidationError("用户名不能超过 10 个字符。")
        return username

    # 对 UserCreationForm 提供的 'password' 字段（即第一个密码字段）进行自定义内容验证
    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            if not re.match(r'^[a-zA-Z0-9]+$', password):
                raise forms.ValidationError("密码必须仅包含字母和数字。")
            if len(password) > 10:
                raise forms.ValidationError("密码不能超过 10 个字符。")
            # 最小长度（例如8位）等其他验证由 settings.py 中的 AUTH_PASSWORD_VALIDATORS 处理
            # UserCreationForm 会自动应用这些验证器
        return password

    # UserCreationForm 中的 clean_password2 方法会检查密码是否匹配，并对 password2 应用验证器
    # 我们可以覆写它，主要是为了自定义不匹配时的错误信息
    def clean_password2(self):
        password = self.cleaned_data.get("password") # 这是 password1
        password2 = self.cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError("两次输入的密码不匹配。")
        
        # 注意：UserCreationForm 的原始 clean_password2 方法也会执行密码验证（来自AUTH_PASSWORD_VALIDATORS）
        # 如果我们完全覆写而不调用 super().clean_password2()，那些验证可能不会在 password2 上执行。
        # 但由于密码匹配检查是最主要的，且Django的字段验证也会在其处理流程中发生，这里我们仅处理匹配错误。
        # 通常，AUTH_PASSWORD_VALIDATORS 主要作用于第一个密码字段，并在 UserCreationForm.save() 时被再次确认。
        return password2 # 必须返回 password2 

class AdminUserEditForm(forms.ModelForm):
    username = forms.CharField(
        label='用户名',
        help_text='必填。10 个字符或更少。仅限字母和数字。',
        max_length=10,
        widget=forms.TextInput(attrs={'style': 'width: 35ch;'})
    )
    email = forms.EmailField(
        label='电子邮箱地址',
        required=False,
        widget=forms.EmailInput(attrs={'style': 'width: 35ch;'}) 
    )
    is_staff = forms.BooleanField(
        label='工作人员状态',
        required=False,
        help_text='指明用户是否可以登录到这个管理站点。'
    )
    is_active = forms.BooleanField(
        label='有效',
        required=False,
        help_text='指明用户是否被认为是活跃的。以反选代替删除帐号。'
    )
    # is_superuser 字段通常不由普通管理员修改，以避免权限问题

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            # Apply form-control class if not already set by specific widget definition
            if 'class' not in self.fields[field_name].widget.attrs:
                 self.fields[field_name].widget.attrs.update({'class': 'form-control'})
            # If size is defined at field level, it takes precedence.
            # Otherwise, could add a default size here if desired, but explicit is better.

        # 如果是编辑超级管理员，则用户名通常不允许修改
        if self.instance and self.instance.pk and self.instance.is_superuser:
            if 'username' in self.fields:
                self.fields['username'].disabled = True
                self.fields['username'].help_text = '超级管理员的用户名不能被修改。'
            # 通常也不允许在此处直接撤销超级管理员权限或活动状态
            if 'is_staff' in self.fields:
                self.fields['is_staff'].disabled = True 
            if 'is_active' in self.fields:
                self.fields['is_active'].disabled = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username: # Ensure username is not None or empty string
            if not re.match(r'^[a-zA-Z0-9]+$', username):
                raise forms.ValidationError("用户名必须仅包含字母和数字。")
            # max_length=10 on the field itself handles the length validation by CharField.
        return username

class AdminSetPasswordForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['new_password1'].label = "新密码"
        self.fields['new_password1'].help_text = '密码必须是字母和数字的组合，不超过10位字符，且不能少于8位。'
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control', 'style': 'width: 35ch;'})
        
        self.fields['new_password2'].label = "确认新密码"
        self.fields['new_password2'].help_text = '请再次输入您的密码进行确认。'
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control', 'style': 'width: 35ch;'}) 