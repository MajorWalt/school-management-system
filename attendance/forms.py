from django import forms
from .models import Attendance

FIELD_CLASS = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"


class AttendanceDateForm(forms.Form):
    """Used to select a date before marking attendance."""

    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": FIELD_CLASS}))


class SingleAttendanceForm(forms.ModelForm):
    """Used per student row when marking attendance."""

    class Meta:
        model = Attendance
        fields = ["status", "note"]
        widgets = {
            "note": forms.TextInput(attrs={"placeholder": "Optional note"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs["class"] = FIELD_CLASS
        self.fields["note"].widget.attrs["class"] = FIELD_CLASS
