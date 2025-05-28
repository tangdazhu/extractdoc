#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖项安装和检查脚本
用于检查和安装文本转换器项目的所有依赖项
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

def run_command(command, description=""):
    """运行命令并返回结果"""
    print(f"正在执行: {description or command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ 成功: {description or command}")
            return True, result.stdout
        else:
            print(f"❌ 失败: {description or command}")
            print(f"错误信息: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {description or command}")
        return False, "命令执行超时"
    except Exception as e:
        print(f"❌ 异常: {description or command} - {str(e)}")
        return False, str(e)

def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro} (满足要求)")
        return True
    else:
        print(f"❌ Python版本: {version.major}.{version.minor}.{version.micro} (需要Python 3.7+)")
        return False

def check_pip():
    """检查pip是否可用"""
    print("🔍 检查pip...")
    
    # 尝试多种pip命令
    pip_commands = ["pip --version", "python -m pip --version", "pip3 --version"]
    
    for cmd in pip_commands:
        success, output = run_command(cmd, f"检查pip版本 ({cmd})")
        if success:
            print(f"✅ pip可用: {cmd}")
            return True
    
    print("❌ 所有pip命令都失败了")
    print("💡 建议:")
    print("   1. 重新安装Python并确保勾选'Add Python to PATH'")
    print("   2. 或者手动安装pip: python -m ensurepip --upgrade")
    return False

def install_requirements():
    """安装requirements.txt中的依赖"""
    print("📦 安装Python依赖包...")
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ 找不到requirements.txt文件: {requirements_file}")
        return False
    
    # 升级pip
    print("⬆️ 升级pip...")
    run_command("python -m pip install --upgrade pip", "升级pip")
    
    # 尝试多种安装命令
    install_commands = [
        f"python -m pip install -r {requirements_file}",
        f"pip install -r {requirements_file}",
        f"pip3 install -r {requirements_file}"
    ]
    
    for cmd in install_commands:
        print(f"📦 尝试安装依赖: {cmd}")
        success, output = run_command(cmd, "安装项目依赖")
        if success:
            print("✅ 依赖安装成功")
            return True
        else:
            print(f"❌ 安装失败，尝试下一个方法...")
    
    print("❌ 所有安装方法都失败了")
    return False

def check_libreoffice():
    """检查LibreOffice是否安装"""
    print("🔍 检查LibreOffice...")
    success, _ = run_command("soffice --version", "检查LibreOffice")
    
    if success:
        print("✅ LibreOffice已安装并可用")
        return True
    else:
        print("⚠️ LibreOffice未安装或不在PATH中")
        print("📝 LibreOffice用于Office文档转换，建议安装:")
        print("   Windows: https://www.libreoffice.org/download/download/")
        print("   Linux: sudo apt-get install libreoffice")
        print("   macOS: brew install --cask libreoffice")
        return False

def check_django_setup():
    """检查Django项目设置"""
    print("🔍 检查Django项目...")
    
    # 检查是否在正确的目录
    manage_py = Path("extract_web/manage.py")
    if not manage_py.exists():
        print("❌ 找不到extract_web/manage.py，请确保在项目根目录运行此脚本")
        return False
    
    # 进入Django项目目录
    os.chdir("extract_web")
    
    # 检查数据库迁移
    print("🗄️ 检查数据库迁移...")
    success, _ = run_command("python manage.py showmigrations", "检查迁移状态")
    
    if success:
        print("📊 执行数据库迁移...")
        success, _ = run_command("python manage.py migrate", "执行数据库迁移")
        
        if success:
            print("✅ 数据库迁移完成")
            return True
    
    return False

def create_superuser():
    """创建超级用户"""
    print("👤 创建管理员用户...")
    print("提示: 如果已存在admin用户，可以跳过此步骤")
    
    try:
        # 尝试创建默认admin用户
        success, _ = run_command(
            'python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser(\'admin\', \'admin@example.com\', \'admin\') if not User.objects.filter(username=\'admin\').exists() else print(\'Admin user already exists\')"',
            "创建默认admin用户"
        )
        
        if success:
            print("✅ 默认管理员用户创建成功 (用户名: admin, 密码: admin)")
        else:
            print("ℹ️ 可以手动创建超级用户: python manage.py createsuperuser")
            
    except Exception as e:
        print(f"⚠️ 创建用户时出错: {e}")
        print("ℹ️ 可以手动创建超级用户: python manage.py createsuperuser")

def main():
    """主函数"""
    print("🚀 文本转换器项目依赖安装脚本")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        print("❌ Python版本不满足要求，请升级到Python 3.7+")
        return False
    
    # 检查pip
    if not check_pip():
        print("❌ pip不可用，请安装pip")
        return False
    
    # 安装Python依赖
    if not install_requirements():
        print("❌ 安装Python依赖失败")
        return False
    
    # 检查LibreOffice
    check_libreoffice()
    
    # 检查Django设置
    if not check_django_setup():
        print("❌ Django项目设置失败")
        return False
    
    # 创建超级用户
    create_superuser()
    
    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n📋 下一步:")
    print("1. 进入Django项目目录: cd extract_web")
    print("2. 启动开发服务器: python manage.py runserver")
    print("3. 在浏览器中访问: http://127.0.0.1:8000/")
    print("4. 使用admin/admin登录管理员账户")
    
    print("\n⚠️ 注意事项:")
    print("- 如果LibreOffice未安装，某些转换功能可能不可用")
    print("- 生产环境请修改默认密码")
    print("- 确保有足够的磁盘空间用于文件转换")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断安装")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装过程中出现未预期的错误: {e}")
        sys.exit(1) 