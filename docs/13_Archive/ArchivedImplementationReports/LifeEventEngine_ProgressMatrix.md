# LIFE EVENT ENGINE — PROGRESS MATRIX

Updated after each event completes. "Report" links to `LifeEvent_<EventName>_ImplementationReport.md`.

| # | Event | Status | Handler | Tests | Report |
|---|---|---|---|---|---|
| 0 | Loan Payoff | ✅ Done (reference) | `loan_payoff_handler.py` | `test_loan_payoff_handler.py` (13) | `LifeEvent_PhaseB1_ImplementationReport.md` |
| 1 | Salary Raise | ✅ Done | `salary_raise_handler.py` | `test_salary_raise_handler.py` (17) | `LifeEvent_SalaryRaise_ImplementationReport.md` |
| 2 | Job Change | ✅ Done | `job_change_handler.py` | `test_job_change_handler.py` (13) | `LifeEvent_JobChange_ImplementationReport.md` |
| 3 | Bonus | ✅ Done | `bonus_handler.py` | `test_bonus_handler.py` (11) | `LifeEvent_Bonus_ImplementationReport.md` |
| 4 | New Loan | ✅ Done | `new_loan_handler.py` | `test_new_loan_handler.py` (16) | `LifeEvent_NewLoan_ImplementationReport.md` |
| 5 | House Purchase | ✅ Done | `house_purchase_handler.py` | `test_house_purchase_handler.py` (16) | `LifeEvent_HousePurchase_ImplementationReport.md` |
| 6 | Home Sale | ✅ Done | `home_sale_handler.py` | `test_home_sale_handler.py` (16) | `LifeEvent_HomeSale_ImplementationReport.md` |
| 7 | Marriage | ✅ Done | `marriage_handler.py` | `test_marriage_handler.py` (14) | `LifeEvent_Marriage_ImplementationReport.md` |
| 8 | Birth of Child | ✅ Done | `birth_of_child_handler.py` | `test_birth_of_child_handler.py` (13) | `LifeEvent_BirthOfChild_ImplementationReport.md` |
| 9 | Adoption | ✅ Done | `birth_of_child_handler.py` (shared) | `test_adoption_handler.py` (7) | `LifeEvent_Adoption_ImplementationReport.md` |
| 10 | Divorce | ✅ Done | `divorce_handler.py` | `test_divorce_handler.py` (16) | `LifeEvent_Divorce_ImplementationReport.md` |
| 11 | Dependent Parent | ✅ Done | `dependent_parent_handler.py` | `test_dependent_parent_handler.py` (14) | `LifeEvent_DependentParent_ImplementationReport.md` |
| 12 | Retirement | ✅ Done | `retirement_handler.py` | `test_retirement_handler.py` (17) | `LifeEvent_Retirement_ImplementationReport.md` |
| 13 | Education Planning | ✅ Done | `education_planning_handler.py` | `test_education_planning_handler.py` (13) | `LifeEvent_EducationPlanning_ImplementationReport.md` |
| 14 | Inheritance | ✅ Done | `inheritance_handler.py` | `test_inheritance_handler.py` (14) | `LifeEvent_Inheritance_ImplementationReport.md` |
| 15 | Major Medical Event | ✅ Done | `major_medical_event_handler.py` | `test_major_medical_event_handler.py` (17) | `LifeEvent_MajorMedicalEvent_ImplementationReport.md` |
| 16 | Business Start | ✅ Done | `business_start_handler.py` | `test_business_start_handler.py` (14) | `LifeEvent_BusinessStart_ImplementationReport.md` |
| 17 | Business Sale | ✅ Done | `business_sale_handler.py` | `test_business_sale_handler.py` (17) | `LifeEvent_BusinessSale_ImplementationReport.md` |

**Legend:** ⏳ Pending/In progress · ✅ Done · 🛑 Blocked (see notes)

## Notes on events not in `LifeEventEngineArchitecture.md`'s original 15-event catalog

Three events in this run's ordered list — **Bonus**, **Dependent Parent**, **Education Planning** — were not designed in the original architecture document. Each is implemented as a minimal, documented extension of an already-established pattern (no new schema, no new mechanism), with the specific design decision recorded in that event's own Implementation Report:
- **Bonus** — modeled as a one-time windfall, same shape as Inheritance (§5.11): creates a liquid Asset (or adds to an existing one), no recurring IncomeSource (a bonus is not ongoing income).
- **Dependent Parent** — identical mechanism to Marriage/Birth of Child (§5.3/§5.5): `family_service.create_member` already supports `relationship_type="parent"` → `dependent_type="elderly_parent"` natively; this event is that exact path with different inputs, nothing new.
- **Education Planning** — a goal-creation event, reusing the existing, already-unconditional `calculate_goal_probability` trigger on goal creation (`routers/goals.py`), same mechanism the optional education-goal step in Birth of Child (§5.5) already uses.
