"""
AtRiskScore rules-v1.

Inputs per student, for the current term:
  - average    : mean of the student's weighted term grades 
  - change     : current term average minus previous term average (same academic year)
  - failing    : number of subjects with a term grade below PASS_MARK
  - behaviour  : demerits minus merits during the term

Each input is turned into a z-score against the student's own form, signed so that
"worse" is always positive, then combined as a weighted sum and mapped to 0-100.
"""

import datetime
import statistics

from django.db import transaction
from django.db.models import Max, Sum

from attendance.utils import get_active_academic_year
from grades.models import Evaluation
from grades.term_grades import load_section_grades, load_term_weights, section_term_grade, weights_for
from merits.models import DemeritRecord, MeritRecord
from scheduling.models import Enrolment, TermConfig
from students.models import Student

from .models import AtRiskScore


MODEL_VERSION = "rules-v1"

PASS_MARK = 55          # term grade below this counts as a failing subject
MIN_PEERS = 5           # forms with fewer scored students are skipped (z-scores unreliable)
FAILING_OVERRIDE = 3    # this many failing subjects is always High
HIGH_THRESHOLD = 70
WATCH_THRESHOLD = 60

# Relative importance of each input. Missing inputs (e.g. no previous term) are dropped and the rest re-normalised.
WEIGHTS = {
    "change": 35,
    "average": 30,
    "failing": 25,
    "behaviour": 10,
}

# +1: higher value = more risk. -1: higher value = less risk.
DIRECTION = {
    "average": -1,
    "change": -1,
    "failing": 1,
    "behaviour": 1,
}


def _mean(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None
    pass


def _resolve_term(school, year, today):
    """(term_number, start_date, end_date) for the term in progress, or None."""
    configs = list(TermConfig.objects.filter(academic_year=year).order_by("term_number"))
    for tc in configs:
        if tc.start_date and tc.end_date and tc.start_date <= today <= tc.end_date:
            return tc.term_number, tc.start_date, tc.end_date
    started = [tc for tc in configs if tc.start_date and tc.start_date <= today]
    if started:
        tc = started[-1]
        return tc.term_number, tc.start_date, tc.end_date or today
    latest = Evaluation.objects.filter(school=school, section__academic_year=year).aggregate(m=Max("section__term_number"))["m"]
    if latest:
        return latest, year.start_date, today
    return None
    pass


def _term_grades(school, year, students, term_numbers):
    """{(student_id, term_number): [term grade, ...]} for courses that count toward averages."""
    enrolments = list(
        Enrolment.objects.filter(
            student__in=students,
            section__school=school,
            section__academic_year=year,
            section__term_number__in=term_numbers,
            section__course__calc_average=True,
        ).select_related("section", "section__course")
    )
    sections = {e.section_id: e.section for e in enrolments}
    evals_by_section, gmap = load_section_grades(school, list(sections), [s.pk for s in students])
    weights_map = load_term_weights(school, sections.values())
    students_by_id = {s.pk: s for s in students}

    out = {}
    for e in enrolments:
        sec = e.section
        evs = evals_by_section.get(sec.pk, [])
        if not evs:
            continue
        grade = section_term_grade(students_by_id[e.student_id], evs, gmap, weights_for(weights_map, sec))
        if grade is not None:
            out.setdefault((e.student_id, sec.term_number), []).append(grade)
    return out
    pass


def _behaviour_totals(school, students, start, end):
    """({student_id: merits}, {student_id: demerits}) between start and end."""
    def totals(model):
        qs = model.objects.filter(school=school, student__in=students, date__lte=end)
        if start:
            qs = qs.filter(date__gte=start)
        return {r["student_id"]: r["total"] or 0 for r in qs.values("student_id").annotate(total=Sum("count"))}

    return totals(MeritRecord), totals(DemeritRecord)
    pass


def _factor_label(key, value, form_mean, features, prev_term):
    if key == "average":
        return f"Average {value:.1f}% (form {form_mean:.1f}%)"
    if key == "change":
        return f"{value:+.1f} pts since Term {prev_term} (form {form_mean:+.1f})"
    if key == "failing":
        return f"{value} subject{'s' if value != 1 else ''} below {PASS_MARK}%"
    if key == "behaviour":
        return f"{features['demerits']} demerits, {features['merits']} merits this term"
    return key
    pass


def compute_school(school, on_date=None):
    """
    Score every enrolled student in one school for the current term and save one
    AtRiskScore row per student for on_date (default today). Safe to re-run.
    Returns a summary dict.
    """
    today = on_date or datetime.date.today()
    summary = {"scored": 0, "skipped_no_grades": 0, "skipped_small_form": 0, "term": None, "year": None, "error": ""}

    year = get_active_academic_year(school)
    if not year:
        summary["error"] = "No active academic year."
        return summary

    term_info = _resolve_term(school, year, today)
    if not term_info:
        summary["error"] = "No term with grades found for the active academic year."
        return summary
    term_number, term_start, term_end = term_info
    prev_term = term_number - 1 if term_number > 1 else None
    behaviour_end = min(term_end, today) if term_end else today

    summary["term"] = term_number
    summary["year"] = year.name

    students = [
        s
        for s in Student.objects.filter(school=school, homeroom__isnull=False, form__isnull=False).select_related("form", "homeroom")
        if s.current_status() == "enrolled"
    ]

    terms = [term_number] + ([prev_term] if prev_term else [])
    grades = _term_grades(school, year, students, terms)
    merits, demerits = _behaviour_totals(school, students, term_start, behaviour_end)

    # Raw features per student
    features = {}
    for s in students:
        current = grades.get((s.pk, term_number), [])
        if not current:
            summary["skipped_no_grades"] += 1
            continue
        avg = _mean(current)
        prev_avg = _mean(grades.get((s.pk, prev_term), [])) if prev_term else None
        m = merits.get(s.pk, 0)
        d = demerits.get(s.pk, 0)
        features[s.pk] = {
            "student": s,
            "average": round(avg, 1),
            "previous_average": round(prev_avg, 1) if prev_avg is not None else None,
            "change": round(avg - prev_avg, 1) if prev_avg is not None else None,
            "failing": sum(1 for g in current if g < PASS_MARK),
            "subjects": len(current),
            "merits": m,
            "demerits": d,
            "behaviour": d - m,
        }

    # Group by form for peer comparison
    by_form = {}
    for f in features.values():
        by_form.setdefault(f["student"].form_id, []).append(f)

    results = []
    for form_id, group in by_form.items():
        if len(group) < MIN_PEERS:
            summary["skipped_small_form"] += len(group)
            continue

        stats = {}
        for key in WEIGHTS:
            vals = [f[key] for f in group if f[key] is not None]
            if len(vals) >= 2:
                stats[key] = (statistics.mean(vals), statistics.pstdev(vals))
            elif vals:
                stats[key] = (vals[0], 0)

        for f in group:
            risk_z = {}
            contributions = {}
            for key, weight in WEIGHTS.items():
                if f[key] is None or key not in stats:
                    continue
                mean, std = stats[key]
                z = (f[key] - mean) / std if std else 0.0
                risk_z[key] = round(DIRECTION[key] * z, 3)
                contributions[key] = weight * risk_z[key]

            used_weight = sum(WEIGHTS[k] for k in contributions)
            combined = sum(contributions.values()) / used_weight if used_weight else 0.0
            score = round(max(0.0, min(100.0, 50 + 20 * combined)), 1)

            override = f["failing"] >= FAILING_OVERRIDE
            if score >= HIGH_THRESHOLD or override:
                band = "high"
            elif score >= WATCH_THRESHOLD:
                band = "watch"
            else:
                band = "low"

            ranked = sorted(((k, c) for k, c in contributions.items() if c > 0), key=lambda kc: kc[1], reverse=True)[:3]
            top_factors = [_factor_label(k, f[k], stats[k][0], f, prev_term) for k, _ in ranked]

            snapshot = {
                "model_version": MODEL_VERSION,
                "term": term_number,
                "previous_term": prev_term,
                "pass_mark": PASS_MARK,
                "inputs": {k: f[k] for k in ("average", "previous_average", "change", "failing", "subjects", "merits", "demerits", "behaviour")},
                "form_means": {k: round(stats[k][0], 2) for k in stats},
                "form_size": len(group),
                "risk_z": risk_z,
                "weights": {k: WEIGHTS[k] for k in contributions},
                "combined_z": round(combined, 3),
                "failing_override": override,
                "top_factors": top_factors,
            }
            results.append((f["student"], score, band, snapshot))

    with transaction.atomic():
        scored_ids = []
        for student, score, band, snapshot in results:
            AtRiskScore.objects.update_or_create(
                student=student,
                computed_on=today,
                defaults={
                    "school": school,
                    "academic_year": year,
                    "term_number": term_number,
                    "score": score,
                    "band": band,
                    "model_version": MODEL_VERSION,
                    "feature_snapshot": snapshot,
                },
            )
            scored_ids.append(student.pk)
        # A re-run the same day replaces the day's results completely
        AtRiskScore.objects.filter(school=school, computed_on=today).exclude(student_id__in=scored_ids).delete()

    summary["scored"] = len(results)
    return summary
    pass