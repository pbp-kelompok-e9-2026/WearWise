from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from carbon_footprint.access import ANALYZER_GROUP


class Command(BaseCommand):
    help = "Buat grup Analyzer dan (opsional) tambahkan user ke dalamnya."

    def add_arguments(self, parser):
        parser.add_argument("usernames", nargs="*", help="Username yang dijadikan analyzer")

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=ANALYZER_GROUP)
        self.stdout.write(f"Grup {ANALYZER_GROUP} {'dibuat' if created else 'sudah ada'}.")
        User = get_user_model()
        for username in options["usernames"]:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' tidak ditemukan.")
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f"{username} sekarang analyzer."))
