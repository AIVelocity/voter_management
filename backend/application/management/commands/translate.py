from django.core.management.base import BaseCommand
from application.models import VoterList
from application.utils.translator import translate_text
import time
import sys

BATCH_SIZE = 300
SLEEP_TIME = 0.8
MAX_RETRIES = 3

class Command(BaseCommand):
    help = "Translate all non-null address_line1 to Marathi"

    def handle(self, *args, **options):

        total_done = 0
        total_failed = 0

        while True:
            qs = VoterList.objects.filter(
                address_line1__isnull=False,
                address_marathi__isnull=True
            ).order_by("voter_list_id")[:BATCH_SIZE]

            batch_count = qs.count()

            if batch_count == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🎉 Translation complete | Done: {total_done} | Failed: {total_failed}"
                    )
                )
                break

            self.stdout.write(
                self.style.WARNING(f"\nProcessing batch of {batch_count} records...")
            )

            for voter in qs:
                try:
                    translated_text = None
                    success = False

                    for attempt in range(MAX_RETRIES):
                        translated_text, success = translate_text(voter.address_line1)
                        if success:
                            break
                        time.sleep(2)

                    if translated_text:
                        voter.address_marathi = translated_text
                        voter.save(update_fields=["address_marathi"])
                        total_done += 1
                    else:
                        total_failed += 1

                    time.sleep(SLEEP_TIME)

                    self.stdout.write(
                        f"✔ Translated ID={voter.voter_list_id}",
                        ending="\r"
                    )

                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.ERROR("\n⛔ Stopped manually. You can safely resume.")
                    )
                    sys.exit(0)

                except Exception as e:
                    total_failed += 1
                    self.stderr.write(
                        f"\n❌ Error for ID {voter.voter_list_id}: {e}"
                    )

