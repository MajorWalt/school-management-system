from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from core.activity import log_activity
from .forms import StaffForm
from .models import Staff


@login_required
@tenant_required
def staff_list(request):
    staff = Staff.objects.filter(school=request.school)
    query = request.GET.get("q", "")
    if query:
        staff = staff.filter(first_name__icontains=query) | staff.filter(last_name__icontains=query) | staff.filter(employee_number__icontains=query)
    return render(request, "staff/staff_list.html", {"staff": staff, "query": query})


@login_required
@tenant_required
def staff_detail(request, pk):
    member = get_object_or_404(Staff, pk=pk, school=request.school)
    return render(request, "staff/staff_detail.html", {"member": member})


@login_required
@tenant_required
def staff_add(request):
    form = StaffForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        staff = form.save(commit=False)
        staff.school = request.school
        staff.save()
        log_activity(request, "staff_add", f"Added staff member {staff.get_full_name()} ({staff.employee_number}).")
        messages.success(request, f"{staff.get_full_name()} added successfully.")
        return redirect("staff:list")
    return render(request, "staff/staff_form.html", {"form": form, "title": "Add Staff Member"})


@login_required
@tenant_required
def staff_edit(request, pk):
    member = get_object_or_404(Staff, pk=pk, school=request.school)
    form = StaffForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request, "staff_edit", f"Edited staff member {member.get_full_name()} ({member.employee_number}).")
        messages.success(request, f"{member.get_full_name()} updated successfully.")
        return redirect("staff:detail", pk=pk)
    return render(request, "staff/staff_form.html", {"form": form, "title": "Edit Staff Member"})


@login_required
@tenant_required
def staff_deactivate(request, pk):
    member = get_object_or_404(Staff, pk=pk, school=request.school)
    member.active = False
    member.save()
    log_activity(request, "staff_deactivate", f"Deactivated staff member {member.get_full_name()} ({member.employee_number}).")
    messages.warning(request, f"{member.get_full_name()} has been deactivated.")
    return redirect("staff:list")


@login_required
@tenant_required
def staff_reactivate(request, pk):
    member = get_object_or_404(Staff, pk=pk, school=request.school)
    member.active = True
    member.save()
    log_activity(request, "staff_reactivate", f"Reactivated staff member {member.get_full_name()} ({member.employee_number}).")
    messages.success(request, f"{member.get_full_name()} has been reactivated.")
    return redirect("staff:list")
