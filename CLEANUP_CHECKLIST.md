# Code Cleanup & Refactoring Checklist

## Priority 1: Consolidate Utility Functions (CRITICAL)

### Task 1.1: Create accounts/utils.py
**Objective:** Consolidate all role/permission checking functions

**Create file with:**
- [ ] `get_roles(user, school)` - from reports/views.py or accounts/templatetags
- [ ] `is_admin(user, school)` - consolidate 5 copies into 1
- [ ] `is_teacher(user, school)` - from accounts/templatetags
- [ ] `is_student(user, school)` - from accounts/templatetags
- [ ] `is_staff_member(user, school)` - admin OR teacher

**Files to update imports:**
- [ ] backups/views.py (line 14) - DELETE is_admin, import from accounts/utils
- [ ] grades/views.py (line 18) - DELETE is_admin, import from accounts/utils
- [ ] reports/views.py (lines 18, 22) - DELETE get_roles & is_admin, import from accounts/utils
- [ ] students/views.py (line 13) - DELETE is_admin, import from accounts/utils
- [ ] students/note_views.py (lines 10-26) - REFACTOR to use accounts/utils

**Estimated effort:** 1 hour
**Files affected:** 6 view files
**Lines saved:** ~50 lines of duplicate code

---

### Task 1.2: Create staff/utils.py
**Objective:** Consolidate staff-related utility functions

**Create file with:**
- [ ] `get_staff_profile(user)` - consolidate 2 copies (grades, reports)
- [ ] `get_hod_departments(staff)` - move from grades/views.py
- [ ] Other staff utilities as needed

**Files to update imports:**
- [ ] grades/views.py (lines 23-28) - DELETE get_teacher_staff, import from staff/utils
- [ ] reports/views.py (lines 26-30) - DELETE get_staff_profile, import from staff/utils
- [ ] grades/views.py (lines 31-36) - DELETE get_hod_departments, import from staff/utils

**Estimated effort:** 30 minutes
**Files affected:** 2 view files
**Lines saved:** ~20 lines

---

### Task 1.3: Create or update scheduling/utils.py or grades/utils.py
**Objective:** Move section/department checking logic

**Add to file:**
- [ ] `section_in_departments(section, departments)` - move from grades/views.py (lines 39-45)

**Files to update imports:**
- [ ] grades/views.py (lines 39-45) - DELETE function, import from utils

**Estimated effort:** 15 minutes
**Files affected:** 1 view file
**Lines saved:** ~10 lines

---

## Priority 2: Remove Unnecessary pass Statements

### Task 2.1: staff/models.py - Remove 5 unnecessary pass statements
**Lines to fix:**
- [ ] Line 142: After `return f"{self.get_full_name()} ({self.employee_number})"`
- [ ] Line 152: After `raise ValidationError(...)`
- [ ] Line 157: After `return " ".join(p for p in parts if p)`
- [ ] Line 161: After `return f"{self.first_name} {self.last_name}"`
- [ ] Line 165: After `return [d for d in [self.department, self.department_2] if d]`

**Estimated effort:** 5 minutes
**Pattern:** Remove all `pass` after `return` or `raise` statements

---

### Task 2.2: grades/views.py - Remove ~20 unnecessary pass statements
**Lines with issues:** 20, 28, 36, 45, 100, 240, 275, 302, ... (full list needed)

**Estimated effort:** 15 minutes
**Pattern:** Systematic removal throughout file

---

### Task 2.3: students/views.py - Remove ~10 unnecessary pass statements
**Estimated effort:** 10 minutes

---

### Task 2.4: students/note_views.py - Remove ~15 unnecessary pass statements
**Lines with issues:** 13, 15, 21, 26, 38, 47, 48, ...

**Estimated effort:** 10 minutes

---

### Task 2.5: Remaining files - Remove ~200 unnecessary pass statements
**Files:** attendance/utils.py, grades/models.py, core/activity.py, etc.

**Estimated effort:** 1-2 hours
**Best approach:** Use automated code formatter (autopep8, ruff, etc.)

---

## Priority 3: Consolidate Decorators

### Task 3.1: Create combined decorator in core/decorators.py
**Objective:** Reduce boilerplate of stacked @login_required + @tenant_required

**Add to core/decorators.py:**
```python
def login_and_tenant_required(view_func):
    """Require login and valid tenant (school)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "school", None):
            raise Http404("No tenant found for this request")
        return view_func(request, *args, **kwargs)
    return wrapper
```

**Estimated effort:** 5 minutes
**Affected:** 80+ view functions

---

### Task 3.2: Replace decorator stacks with combined decorator
**Files to update:**
- [ ] grades/views.py: Replace 28 stacked decorators with @login_and_tenant_required
- [ ] students/views.py: Replace 10 stacked decorators
- [ ] students/note_views.py: Replace 3 stacked decorators
- [ ] reports/views.py: Replace 7 stacked decorators
- [ ] Other view files as needed

**Estimated effort:** 1-2 hours
**Lines saved:** ~160 lines (80 decorators * 2 lines each)

---

## Priority 4: Fix Fragile Imports

### Task 4.1: Fix students/views.py import
**Current (line 75):**
```python
from .note_views import _is_staff, _is_admin
```

**Issue:** Imports from note_views instead of centralized location

**Fix:**
- [ ] Update students/note_views.py to not use underscore prefix
- [ ] Or move _is_staff, _is_admin to accounts/utils.py
- [ ] Update import in students/views.py

**Estimated effort:** 30 minutes
**Impact:** Improves code organization and testability

---

### Task 4.2: Consolidate note_views utility functions
**File:** students/note_views.py (lines 10-26)

**Current functions:**
- `_roles(user, school)` - underscore prefix
- `_is_staff(user, school)` - underscore prefix
- `_is_admin(user, school)` - underscore prefix

**Options:**
1. Move to accounts/utils.py and remove underscore
2. Keep in note_views.py but remove underscore prefix (make public)
3. Create students/utils.py for student-specific utility functions

**Recommendation:** Move to accounts/utils.py - consolidates all role checks

**Estimated effort:** 20 minutes

---

## Priority 5: Improve Large Files

### Task 5.1: Document reports/views.py complexity
**File:** reports/views.py (1,055 lines - LARGEST)

**Action items:**
- [ ] List all view functions and their purposes
- [ ] Identify logical groupings (student reports, staff reports, etc.)
- [ ] Plan future refactoring into separate modules

**Estimated effort:** 30 minutes
**Future:** Consider splitting into multiple files

---

### Task 5.2: Document grades/views.py complexity
**File:** grades/views.py (884 lines - SECOND LARGEST)

**Action items:**
- [ ] List all view functions and their purposes
- [ ] Identify opportunities for shared utility functions
- [ ] Plan future refactoring if needed

**Estimated effort:** 30 minutes

---

## Priority 6: HOD Feature Validation

### Task 6.1: Create HOD feature documentation
**Deliverable:** HOD_FEATURE_DOCUMENTATION.md

**Content:**
- [ ] What HOD can do
- [ ] What HOD cannot do
- [ ] Database schema changes
- [ ] Code locations (models, views, forms, templates)
- [ ] Access control rules
- [ ] Testing scenarios

**Estimated effort:** 1 hour

---

### Task 6.2: Create HOD feature tests
**File:** tests/test_hod_features.py (NEW)

**Test cases:**
- [ ] Staff member can be marked as HOD only with department
- [ ] HOD sees correct departments
- [ ] HOD can view grades in their department
- [ ] HOD cannot edit grades (read-only)
- [ ] Non-HOD staff cannot see other sections
- [ ] Admin sees all sections regardless

**Estimated effort:** 2 hours

---

### Task 6.3: Verify HOD access control
**Verification checklist:**
- [ ] HOD access properly scoped in grades_home()
- [ ] HOD access properly scoped in section_grade_table()
- [ ] No other modules need HOD access (merits, attendance, reports)
- [ ] Template correctly shows is_hod_view flag
- [ ] Access denied properly handled for non-HOD/non-owner

**Estimated effort:** 1 hour

---

## Summary of Changes

| Task | Priority | Effort | Impact | Files |
|------|----------|--------|--------|-------|
| Consolidate utility functions | Critical | 2 hours | High | 6 view files |
| Remove pass statements | High | 2-3 hours | Medium | 12+ files |
| Consolidate decorators | Medium | 2-3 hours | Medium | 80+ locations |
| Fix fragile imports | High | 1 hour | High | 2 files |
| Improve large files | Low | 1 hour | Low | 2 files |
| HO
