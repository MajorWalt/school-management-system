import datetime

from django.core.management.base import BaseCommand

from core.models import School
from analytics.scoring import compute_school


class Command(BaseCommand):
    help = "Compute AtRiskScore (rules-v1) for every school, or one school with --school <id>. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--school", type=int, help="Only this school id.")

    def handle(self, *args, **options):
        schools = School.objects.all()
        if options.get("school"):
            schools = schools.filter(pk=options["school"])

        started = datetime.datetime.now()
        self.stdout.write(f"[{started:%Y-%m-%d %H:%M:%S}] compute_risk_scores started")

        for school in schools:
            try:
                r = compute_school(school)
                if r["error"]:
                    self.stdout.write(f"  {school}: skipped - {r['error']}")
                else:
                    self.stdout.write(
                        f"  {school}: {r['year']} Term {r['term']} - scored {r['scored']}, "
                        f"no grades {r['skipped_no_grades']}, small form {r['skipped_small_form']}"
                    )
            except Exception as e:
                self.stderr.write(f"  {school}: FAILED - {e}")

        self.stdout.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] done")