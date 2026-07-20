# Head of Department (HOD) Feature Documentation

**Last Updated:** July 20, 2026  
**Status:** Implemented and Tested ✅  
**Test Coverage:** 26 comprehensive tests (all passing)

---

## Overview

The Head of Department feature allows staff members to be designated as Heads of their academic departments and provides them with expanded access to view grades across all sections in their departments.

---

## Database Schema

### Staff Model Fields

The `Staff` model includes two new fields for HOD management:

```python
is_head_of_department = BooleanField(default=False, verbose_name="Head of Department")
department_2 = CharField(max_length=100, choices=DEPARTMENT_CHOICES, blank=True, 
                         verbose_name="Second department")
```

### Database Constraints

Two CHECK constraints enforce data integrity:

1. **`hod_requires_department`**: A staff member cannot be marked as HOD without a primary department
   - If `is_head_of_department=True`, then `department` must not be empty

2. **`second_department_requires_first`**: A secondary department can only exist if a primary department is set
   - If `department_2` is not empty, then `department` must not be empty

### Additional Validation

The model's `clean()` method provides additional validation:
- Staff cannot be HOD without a department
- Primary and secondary departments must be different
- Secondary department cannot exist without a primary department

---

## Features

### 1. Model-Level Management

#### Creating an HOD

```python
# Single department HOD
hod_staff = Staff.objects.create(
    school=school,
    employee_number="EMP100",
    first_name="John",
    last_name="Doe",
    department="Mathematics",
    is_head_of_department=True
)

# Multi-department HOD
hod_staff = Staff.objects.create(
    school=school,
    employee_number="EMP101",
    first_name="Jane",
    last_name="Smith",
    department="English",
    department_2="Modern Languages",
    is_head_of_department=True
)
```

#### Helper Methods

**`staff.get_departments()`** - Returns list of departments the staff heads

```python
hod = Staff.objects.get(is_head_of_department=True)
depts = hod.get_departments()  # Returns ['Mathematics'] or ['English', 'Modern Languages']
```

### 2. Form Support

The staff form (`staff/forms.py`) includes:
- **HOD Checkbox** - Enable/disable HOD status
- **Secondary Department Field** - Select an optional second department

The form handles all validation rules automatically.

### 3. View-Level Access Control

#### Utility Functions in `grades/views.py`

**`get_hod_departments(staff)`** - Get departments managed by an HOD

```python
staff = request.user.staff_profile
hod_depts = get_hod_departments(staff)
# Returns: [] if not HOD, ['dept1', 'dept2'] if HOD
```

**`section_in_departments(section, departments)`** - Check if section belongs to list of departments

```python
sections = Section.objects.filter(school=school)
hod_depts = get_hod_departments(staff)

for section in sections:
    if section_in_departments(section, hod_depts):
        # HOD can view/manage this section
```

### 4. Grade Access

HOD users can view grades for:
1. Sections they teach directly (as teacher)
2. All sections in their managed departments

**Location:** `grades/grades_home()` view (lines 48-93 in grades/views.py)

```python
if admin:
    sections = Section.objects.filter(school=school)
elif staff:
    hod_departments = get_hod_departments(staff)
    if hod_departments:
        # Can see: own sections + department sections
        sections = Section.objects.filter(school=school).filter(
            Q(teacher=staff) | Q(course__department__in=hod_departments)
        )
    else:
        # Can only see: own sections
        sections = Section.objects.filter(school=school, teacher=staff)
```

### 5. Template Display

The staff detail template displays:
- HOD status badge/indicator
- Primary department
- Secondary department (if set)

---

## Access Permissions

### Who Can Create/Edit HOD Status?

- **Admins only** - Only school administrators can designate or remove HOD status

### What Can HODs Do?

| Feature | Regular Teacher | HOD | Admin |
|---------|-----------------|-----|-------|
| View own section grades | ✅ | ✅ | ✅ |
| View dept section grades | ❌ | ✅ | ✅ |
| Edit grades | Limited* | Limited* | ✅ |
| View student reports | Limited* | Limited* | ✅ |
| Access merits/attendance | Limited* | Limited* | ✅ |
| View department staff | ❌ | ❌ | ✅ |
| Manage HOD assignments | ❌ | ❌ | ✅ |

*Limited = Teacher/HOD can only manage their direct students/sections

### Read vs Edit Permissions

**Current Implementation:** HOD grade access is **READ-ONLY**
- HODs can view grades for their department's sections
- HODs cannot edit grades for sections they don't teach
- Grade editing remains restricted to the teaching staff member

---

## Implementation Details

### Locations in Codebase

| Component | Location | Lines |
|-----------|----------|-------|
| Model | `staff/models.py` | 99-108, 144-151 |
| Form | `staff/forms.py` | 36, 67-71 |
| Template (form) | `templates/staff/staff_form.html` | N/A |
| Template (detail) | `templates/staff/staff_detail.html` | N/A |
| View utilities | `grades/views.py` | 17-35 |
| Grade access logic | `grades/views.py` | 48-93 |
| Tests | `tests/test_hod_features.py` | All 26 tests |

### Database Migration

Migration: `staff/migrations/0002_staff_department_2_staff_is_head_of_department_and_more.py`

Changes:
- Added `is_head_of_department` BooleanField (default=False)
- Added `department_2` CharField (blank=True)
- Added `hod_requires_department` CHECK constraint
- Added `second_department_requires_first` CHECK constraint

---

## Testing

### Test Coverage: 26 Tests (All Passing ✅)

#### Model Tests (10 tests)
- Default value validation
- Single/dual department creation
- Validation rules (same department prevention)
- Helper methods (get_departments)

#### Access Control Tests (8 tests)
- Department retrieval for HOD/non-HOD
- Section-in-department checks
- Multiple department access

#### Form Tests (5 tests)
- HOD checkbox presence
- Secondary department field
- Form submission with HOD data
- Editing to make staff HOD

#### View Tests (2 tests)
- Detail page displays HOD status
- Detail page shows departments

#### Utility Tests (3 tests)
- is_admin() function
- Superuser handling
- Role-based access

**Run tests:**
```bash
python manage.py test tests.test_hod_features -v 2
```

---

## Configuration

### Department Choices

HODs can manage any of the following departments:

- Mathematics
- English / Language Arts
- Natural Sciences
- Social Studies
- Modern Languages
- Information Technology
- Business Studies
- Physical Education
- Visual & Performing Arts
- Technical
- Religious Education
- Building & Technical Drawing
- Geography
- History
- Agriculture

---

## Future Enhancements

### Potential Additions

1. **HOD Permissions Matrix**
   - Granular control over what HODs can do
   - Edit vs. view permissions configuration

2. **Department Reports**
   - Dedicated HOD dashboard
   - Department-wide performance analytics
   - Staff management within department

3. **Grade Appeals**
   - HODs review grade disputes
   - Approval workflow

4. **Attendance Oversight**
   - HODs view dept attendance reports
   - Track teacher attendance patterns

5. **Merit/Demerit Oversight**
   - HODs review dept merit records
   - Trend analysis

### Considerations for Implementation

- Multi-tenant isolation (ensure HODs can't access other schools' depts)
- Activity logging (who approved/changed HOD status)
- Audit trail for grade access by HOD

---

## Troubleshooting

### Common Issues

**Q: Staff member can't be marked as HOD**
- Ensure a primary department is selected before enabling HOD checkbox

**Q: Can't set a second department**
- First, save the staff member with a primary department
- Then add the secondary department (must be different from primary)

**Q: HOD can't see section grades**
- Verify the section's course is assigned to one of HOD's departments
- Check that section exists in same school

**Q: Database error: "CHECK constraint failed"**
- This is normal validation - violates one of the constraints
- See "Database Constraints" section above

---

## API Reference

### Utility Functions

#### `get_hod_departments(staff: Staff) -> List[str]`

**Returns:** List of department strings that staff member heads

**Parameters:**
- `staff`: Staff instance

**Example:**
```python
from grades.views import get_hod_departments

staff = Staff.objects.get(user=request.user)
depts = get_hod_departments(staff)
print(depts)  # ['Mathematics', 'Natural Sciences']
```

#### `section_in_departments(section: Section, departments: List[str]) -> bool`

**Returns:** True if section belongs to any department in list

**Parameters:**
- `section`: Section instance
- `departments`: List of department strings

**Example:**
```python
from grades.views import section_in_departments

section = Section.objects.get(pk=1)
hod_depts = ['Mathematics', 'English']
can_view = section_in_departments(section, hod_depts)
```

---

## Related Features

- **Role-Based Access Control** - Integrated with existing role system
- **Grade Entry** - Read-only access from HOD interface
- **Staff Management** - Admin-only HOD assignment
- **Section Filtering** - Dynamic filtering based on HOD status

---

## Contact & Support

For questions about the HOD feature:
1. Review this documentation
2. Check test cases in `tests/test_hod_features.py`
3. Review grades/views.py for access control logic
4. Review staff/models.py for validation rules
