from django.core.management.base import BaseCommand

from game.account_lifecycle import purge_expired_archives


class Command(BaseCommand):
    help = "Permanently purge player account archives past their two-year recovery period."

    def handle(self, *args, **options):
        count = purge_expired_archives()
        self.stdout.write(self.style.SUCCESS(f"Purged {count} expired account archive(s)."))
