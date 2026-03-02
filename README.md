# Parivaar Health — Family Health Management Platform

A **caregiver-first**, multi-member family health management Django web application.

---

## Features

### ✅ Phase 1 MVP Implemented

| Module | Features |
|---|---|
| **Family Account Setup** | Register, create family profile, add members, roles (Admin/Member/View-only), invite flow |
| **Family Dashboard** | Command center with today's items, alerts panel, monthly snapshot, quick actions |
| **Medicine Cabinet** | Add medicines, stock tracking, expiry alerts, low stock alerts, refill management |
| **Shared Calendar** | Appointments by member, daily/monthly views, status tracking, completion toggle |
| **Reports Vault** | Upload PDF/images, metadata tagging, search & filter, ABHA linking support |
| **Family Summary** | Household-level insights (non-diagnostic), per-member snapshots |
| **Emergency View** | Quick printable family health summary for emergencies |

---

## Tech Stack

- **Backend**: Django 4.2 with Class-Based Views
- **Database**: SQLite (dev) — easily swap to PostgreSQL for production
- **Frontend**: Bootstrap 5.3 + Bootstrap Icons
- **Storage**: Local media (configure S3 for production)
- **Auth**: Django's built-in authentication with role-based access

---

## Project Structure

```
parivaar_health/
├── parivaar_health/       # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/              # Family & Member management
│   ├── models.py          → Family, FamilyMember, ChronicCondition, ConsentLog
│   ├── views.py           → CBVs: Register, Login, Family CRUD, Member CRUD
│   ├── forms.py
│   └── urls.py
├── core/                  # Dashboard & Summary
│   ├── views.py           → DashboardView, FamilySummaryView
│   └── urls.py
├── medicines/             # Medicine Cabinet
│   ├── models.py          → Medicine, MedicineReminder, MedicineRefillRequest
│   ├── views.py           → Medicine CRUD, Stock Update, Reminder tracking
│   ├── forms.py
│   └── urls.py
├── calendar_app/          # Appointments
│   ├── models.py          → Appointment
│   ├── views.py           → Appointment CRUD, Status updates, Calendar view
│   ├── forms.py
│   └── urls.py
├── vault/                 # Reports Vault
│   ├── models.py          → Report, VaultAccessLog
│   ├── views.py           → Report CRUD, Emergency View
│   ├── forms.py
│   └── urls.py
├── templates/             # All HTML templates
│   ├── base.html
│   ├── accounts/
│   ├── core/
│   ├── medicines/
│   ├── calendar_app/
│   └── vault/
├── manage.py
├── requirements.txt
└── setup.sh
```

---

## Data Models & Relationships

```
User (Django Auth)
 └── Family (admin: OneToOne → User)
      └── FamilyMember (family: FK → Family, user: OneToOne → User [optional])
           ├── ChronicCondition (member: FK → FamilyMember)
           ├── ConsentLog (member: FK → FamilyMember)
           ├── Medicine (member: FK → FamilyMember)
           │    ├── MedicineReminder (medicine: FK → Medicine)
           │    └── MedicineRefillRequest (medicine: FK → Medicine)
           ├── Appointment (family: FK → Family, member: FK → FamilyMember)
           └── Report (family: FK → Family, member: FK → FamilyMember)
                └── VaultAccessLog (report: FK → Report)
```

---

## Quick Start

### 1. Install & Setup
```bash
cd parivaar_health
pip install -r requirements.txt
python manage.py makemigrations accounts medicines calendar_app vault
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Or run the setup script:
```bash
chmod +x setup.sh && ./setup.sh
```

### 2. Register & Onboard
1. Visit `http://127.0.0.1:8000/accounts/register/`
2. Create your account (Step 1)
3. Create your family profile (Step 2)
4. Add family members (Step 3)
5. You're on the Dashboard!

---

## URL Map

| URL | View | Description |
|---|---|---|
| `/` | Redirect → Dashboard | Home |
| `/accounts/register/` | RegisterView | New user signup |
| `/accounts/login/` | CustomLoginView | Login |
| `/accounts/family/create/` | FamilyCreateView | Onboarding: create family |
| `/accounts/members/` | FamilyMemberListView | Family members list |
| `/dashboard/` | DashboardView | Main command center |
| `/family-summary/` | FamilySummaryView | Family insights |
| `/medicines/` | MedicineListView | Medicine cabinet |
| `/medicines/add/` | MedicineCreateView | Add medicine |
| `/medicines/reminders/today/` | TodayRemindersView | Daily dose tracker |
| `/calendar/` | AppointmentListView | All appointments |
| `/calendar/add/` | AppointmentCreateView | Schedule appointment |
| `/vault/` | ReportListView | Reports vault |
| `/vault/upload/` | ReportUploadView | Upload report |
| `/vault/emergency/` | EmergencyViewView | Emergency summary |
| `/admin/` | Django Admin | Full backend admin |

---

## Role-Based Access

| Feature | Admin | Member | View-Only |
|---|---|---|---|
| Create/edit family | ✅ | ❌ | ❌ |
| Add/edit members | ✅ | ❌ | ❌ |
| Manage all medicines | ✅ | Own only | ❌ |
| Upload reports | ✅ | Own only | ❌ |
| View dashboard | ✅ | Limited | Read-only |
| Emergency view | ✅ | ❌ | ❌ |

---

## Production Checklist

- [ ] Change `SECRET_KEY` in settings.py
- [ ] Set `DEBUG = False`
- [ ] Configure PostgreSQL database
- [ ] Set up AWS S3 for media storage
- [ ] Configure SMTP for email
- [ ] Set up WhatsApp Business API for reminders
- [ ] Enable ABHA API integration
- [ ] Set `ALLOWED_HOSTS` appropriately
- [ ] Use `gunicorn` + `nginx` for deployment
