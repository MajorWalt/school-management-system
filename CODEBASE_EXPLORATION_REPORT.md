# School Management System - Codebase Exploration Report

**Date:** July 20, 2026  
**Project:** Django-based School Management System  
**Total Python Files:** 164 (excluding virtual environment)  
**Total HTML Templates:** 86

---

## 1. PROJECT STRUCTURE OVERVIEW

### Main Application Modules

```
school-management-system/
├── accounts/           # User authentication & roles
├── attendance/         # Student/staff attendance tracking
├── backups/            # Database backup management
├── branding/           # School branding/theming
├── config/             # Django settings & configuration
├── core/               # Core utilities, decorators, middleware
├── grades/             # Grade entry, evaluation, reporting
├── merits/             # Merit/demerit system
├── portals/            # User dashboards (admin/teacher/student)
├── reports/            # Report generation
├── scheduling/         # Academic year, terms, classes, sections
├── staff/              # Staff member management
├── students/           # Student management
├── templates/          # HTML templates
├── static/             # Static files (CSS, JS)
└── media/              # User uploads
```

### Key Dependencies
- Django 6.0.6
- Multi-tenancy support (school-based isolation)
- Role-based access control (RBAC)
- Custom decorators for permission management

---

## 2. CODEBASE STATISTICS

### File Count by Type
- **View Files:** 12 (views.py files)
- **Model Files:** 8 main model modules
- **Form Files:** 4 (staff, grades, attendance, students, merits)
- **Utility Files:** 6+ (utils.py files across modules)
- **Test Files:** 9 test modules
- **Migration Files:** 25+

### Code Complexity
- **Largest file:** reports/views.py (1,055 lines)
- **Second largest:** grades/views.py (884 lines)
- **Third largest:** students/views.py (437 lines)

### Code Quality Issues
- **Total unnecessary pass statements:** 246 instances
- **Duplicate function definitions:** 7 (is_admin functions)
- **Duplicate role check functions:** Multiple (_is_admin, _is_staff)

---

## 3. HEAD OF DEPARTMENT (HOD) FEATURE - RECENTLY ADDED

### Migration Details
**File:** staff/migrations/0002_staff_department_2_staff_is_head_of_department_and_more.py  
**Date:** July 20, 2026

### Database Schema Changes
1. **New Field:** Staff.is_head_of_department (BooleanField)
2. **New Field:** Staff.department_2 (CharField - second department)
3. **New Constraint:** hod_requires_department - HOD must have a department assigned
4. **New Constraint:** second_department_requires_first - Second dept requires primary dept

### Model Implementation
**File:** staff/models.py (lines 101-165)

- Head of Department flag as boolean field
- Validation: Cannot be HOD without a department
- Validation: Second department must differ from primary
- Check constraints in Meta class

### Form Implementation
**File:** staff/forms.py (lines 36, 67-71)

- Form includes is_head_of_department checkbox field
- Field is disabled until a department is selected
- Uses Alpine.js for frontend validation/UX

### Template Updates
**Files:**
- templates/staff/staff_form.html (lines 67-97) - Form with HOD checkbox
- templates/staff/staff_detail.html (lines 12-13, 80-81) - HOD badge display

### HOD Feature Usage in Grades
**File:** grades/views.py

**Key Functions:**
1. get_hod_departments(staff) - Returns departments where staff is HOD
2. section_in_departments(section, departments) - Checks department membership
3. grades_home() - HOD sees sections they teach + departmental sections
4. section_grade_table() - HOD can view departmental grades

### Access Control for HOD
- Can view grades for sections in their departments
- Can view student records for their department
- Cannot create new grades or evaluations
- Read-only access (indicated by is_hod_view template flag)

---

## 4. CODE DUPLICATION & REDUNDANCY

### 4.1 Duplicate is_admin() Functions

**CRITICAL ISSUE:** The is_admin() function is defined identically in 5 locations:

1. accounts/templatetags/accounts_tags.py (line 16) - Template tag version
2. backups/views.py (line 14)
3. grades/views.py (line 18)
4. reports/views.py (line 22)
5. students/views.py (line 13)

**Code (identical in all):**
```python
def is_admin(user, school):
    return UserRole.objects.filter(user=user, school=school, role="admin").exists() or user.is_superuser
```

**Recommendation:** Move to shared utility module like core/utils.py

### 4.2 Duplicate Role Check Functions

**Issue:** Similar but inconsistently named role check functions

**Locations:**
- students/note_views.py (lines 10-26): _roles(), _is_staff(), _is_admin()
- accounts/templatetags/accounts_tags.py: get_roles(), is_admin(), is_teacher(), is_student(), etc.
- reports/views.py: get_roles(), is_admin()

**Problem:**
- Inconsistent naming (underscore vs no underscore)
- Duplicated logic
- Fragile dependencies (students/views imports from note_views)

### 4.3 Pattern: Get User's Staff Profile

**Locations:**
- grades/views.py (lines 23-28): get_teacher_staff()
- reports/views.py (lines 26-30): get_staff_profile()

**Note:** Same function, different names

### 4.4 Repeated Decorator Pattern

**Issue:** Consistent stacking of @login_required + @tenant_required

**Count:** 283 total decorator usages  
**Potential:** Could create combined @login_and_tenant_required decorator

### 4.5 Unnecessary pass Statements

**Total:** 246 unnecessary pass statements

**Top files:**
- attendance/utils.py: 15+ instances
- grades/views.py: 20+ instances
- grades/models.py: 8+ instances
- students/views.py: 10+ instances
- staff/models.py: 5 instances (lines 142, 152, 157, 161, 165)

**Example from staff/models.py:**
```python
def __str__(self):
    return f"{self.get_full_name()} ({self.employee_number})"
    pass  # <- Unnecessary

def get_full_name(self):
    return " ".join(p for p in parts if p)
    pass  # <- Unnecessary after return
```

---

## 5. SPECIFIC FILES NEEDING CLEANUP

### HIGH PRIORITY

#### 5.1 staff/models.py
- **Lines:** 142, 152, 157, 161, 165 (unnecessary pass statements)
- **Action:** Remove trailing pass statements after return statements

#### 5.2 core/decorators.py
- **Lines:** 23-99
- **Action:** Consider creating combined decorator for @login_required + @tenant_required
- **Benefit:** Reduce boilerplate across 80+ view functions

#### 5.3 grades/views.py (884 lines)
- **Lines:** 18-20, 23-28, 31-36, 39-45 (utility functions)
- **Action:** Move to shared modules:
  - is_admin() → core/utils.py
  - get_teacher_staff() → staff/utils.py
  - get_hod_departments() → staff/utils.py
  - section_in_departments() → scheduling/utils.py or grades/utils.py
- **Trailing pass:** 20+ instances throughout file

#### 5.4 students/views.py (437 lines)
- **Lines:** 13-15 (duplicate is_admin)
- **Lines:** 75 (fragile import from note_views)
- **Action:** Remove duplicate is_admin, import from shared utility
- **Trailing pass:** 10+ instances

#### 5.5 students/note_views.py (101 lines)
- **Lines:** 10-26 (utility functions with underscore prefix)
- **Action:** Consolidate or rename to remove underscore prefix
- **Trailing pass:** 15+ instances

#### 5.6 backups/views.py
- **Lines:** 14-15 (duplicate is_admin)
- **Action:** Remove, import from shared utility

#### 5.7 reports/views.py (1,055 lines - LARGEST FILE)
- **Lines:** 18-24 (duplicate functions: get_roles, is_admin)
- **Action:** Remove, import from shared utilities
- **Size:** 1,055 lines - consider breaking into separate modules

### MEDIUM PRIORITY

#### 5.8 staff/forms.py
- **Lines:** 68-71
- **Action:** Consider extracting Alpine.js directives to separate file
- **Benefit:** Cleaner HTML templates, reusable validation logic

#### 5.9 accounts/templatetags/accounts_tags.py
- **Status:** Already properly centralized - use as primary source
- **Action:** Ensure all modules import from here

#### 5.10 core/context_processors.py
- **Action:** Verify it uses centralized role check functions
- **Benefit:** Consistency across all template contexts

---

## 6. DUPLICATION SUMMARY TABLE

| Function | Locations | Status |
|----------|-----------|--------
