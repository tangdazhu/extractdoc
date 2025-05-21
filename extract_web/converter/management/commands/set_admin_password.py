from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Sets the password for the admin user to a predefined value.'

    def handle(self, *args, **options):
        try:
            admin = User.objects.get(username='admin')
            admin.set_password('admin')
            admin.save()
            self.stdout.write(self.style.SUCCESS("Successfully set password for admin user."))
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR("Admin user does not exist. Please create it first.")) 