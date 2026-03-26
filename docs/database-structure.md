# TellTake Database Architecture

## Overview

TellTake uses a **NIST Core RBAC** (Role-Based Access Control) model backed by PostgreSQL.
The central principle is:

> **Permission = Action + Resource**

A permission is not a generic label — it is a concrete, atomic capability such as
"CREATE on users" or "DELETE on reports". Roles aggregate permissions, and users are
assigned roles.

---

## High-Level Design (HLD)

### Authorization Chain

```
AdminUser ──M:N──> Role ──M:N──> Permission ──FK──> Resource
                                  (action)        (resource_name)
```

### Access Check Flow

```
Incoming Request
       │
       ▼
 Auth Middleware
       │
       ▼
 Extract User from Token
       │
       ▼
 is_superuser? ── Yes ──> ALLOW
       │
      No
       │
       ▼
 is_active? ── No ──> DENY
       │
      Yes
       │
       ▼
 Load User Roles (filter is_active=True)
       │
       ▼
 Any role has Permission(action=Y, resource=Z)? ── Yes ──> ALLOW
       │
      No
       │
       ▼
     DENY
```

### Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Primary key type | UUID v4 | Globally unique, safe for distributed systems, no sequential leakage |
| Soft deletes | `deleted_at` timestamp | Audit trail; rows are never physically removed |
| Password hashing | Argon2id (via `argon2-cffi`) | Winner of the Password Hashing Competition, memory-hard |
| Email storage | CITEXT (case-insensitive) | Prevents duplicate emails differing only by case |
| Relationship loading | `lazy="selectin"` | Avoids N+1 queries; loads related objects in a single extra SELECT |
| Permission uniqueness | `UNIQUE(action, resource_id)` | Prevents duplicate permission rows for the same action-resource pair |
| Cascade deletes | `ON DELETE CASCADE` on all FKs | Removing a role auto-cleans junction rows |

---

## Low-Level Design (LLD)

### Entity-Relationship Diagram

```
┌──────────────────────────────────────────────────┐
│                   admin_users                     │
├──────────────────────────────────────────────────┤
│ id            UUID         PK, default uuid4     │
│ email         CITEXT       NOT NULL, UNIQUE, IDX │
│ username      VARCHAR      NOT NULL, UNIQUE, IDX │
│ first_name    VARCHAR      IDX                   │
│ last_name     VARCHAR      IDX                   │
│ full_name     VARCHAR      IDX                   │
│ password_hash VARCHAR      NOT NULL               │
│ is_active     BOOLEAN      DEFAULT TRUE           │
│ is_superuser  BOOLEAN      DEFAULT FALSE          │
│ created_at    TIMESTAMPTZ  server_default now()   │
│ updated_at    TIMESTAMPTZ  on update              │
│ deleted_at    TIMESTAMPTZ  nullable (soft delete) │
└──────────────────────────────────────────────────┘
        │
        │ M:N via user_roles
        ▼
┌──────────────────────────────────────────────────┐
│                   user_roles                      │
│              (junction / association)              │
├──────────────────────────────────────────────────┤
│ user_id       UUID    PK, FK -> admin_users.id   │
│ role_id       UUID    PK, FK -> roles.id         │
│                       ON DELETE CASCADE           │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│                     roles                         │
├──────────────────────────────────────────────────┤
│ id            UUID         PK, default uuid4     │
│ role_name     VARCHAR      NOT NULL, UNIQUE       │
│ description   VARCHAR      nullable               │
│ is_active     BOOLEAN      NOT NULL, DEFAULT TRUE │
│ created_at    TIMESTAMPTZ  server_default now()   │
│ updated_at    TIMESTAMPTZ  on update              │
│ deleted_at    TIMESTAMPTZ  nullable (soft delete) │
└──────────────────────────────────────────────────┘
        │
        │ M:N via role_permissions
        ▼
┌──────────────────────────────────────────────────┐
│               role_permissions                    │
│              (junction / association)              │
├──────────────────────────────────────────────────┤
│ role_id       UUID    PK, FK -> roles.id         │
│ permission_id UUID    PK, FK -> permissions.id   │
│                       ON DELETE CASCADE           │
└──────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│                  permissions                      │
├──────────────────────────────────────────────────┤
│ id            UUID           PK, default uuid4   │
│ action        action_type_enum  NOT NULL          │
│               (CREATE|READ|UPDATE|DELETE|MANAGE)  │
│ resource_id   UUID           FK -> resources.id  │
│                              NOT NULL, CASCADE    │
│ description   VARCHAR        nullable             │
│ created_at    TIMESTAMPTZ    server_default now() │
│ updated_at    TIMESTAMPTZ    on update            │
│ deleted_at    TIMESTAMPTZ    nullable (soft del)  │
│                                                   │
│ UNIQUE(action, resource_id)                       │
│   name: uq_permission_action_resource             │
└──────────────────────────────────────────────────┘
        │
        │ FK (many-to-one)
        ▼
┌──────────────────────────────────────────────────┐
│                   resources                       │
├──────────────────────────────────────────────────┤
│ id            UUID         PK, default uuid4     │
│ resource_name VARCHAR      NOT NULL, UNIQUE       │
│ description   VARCHAR      nullable               │
│ created_at    TIMESTAMPTZ  server_default now()   │
│ updated_at    TIMESTAMPTZ  on update              │
│ deleted_at    TIMESTAMPTZ  nullable (soft delete) │
└──────────────────────────────────────────────────┘
```

---

## Table Details

### admin_users

Stores administrator accounts with authentication credentials.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated v4 |
| `email` | CITEXT | NOT NULL, UNIQUE, INDEX | Case-insensitive |
| `username` | VARCHAR | NOT NULL, UNIQUE, INDEX | |
| `first_name` | VARCHAR | INDEX | |
| `last_name` | VARCHAR | INDEX | |
| `full_name` | VARCHAR | INDEX | |
| `password_hash` | VARCHAR | NOT NULL | Argon2id hash |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account enabled flag |
| `is_superuser` | BOOLEAN | DEFAULT FALSE | Bypasses all permission checks |
| `created_at` | TIMESTAMPTZ | NOT NULL | Server-side default |
| `updated_at` | TIMESTAMPTZ | | Auto-set on update |
| `deleted_at` | TIMESTAMPTZ | | Soft delete marker |

**Relationships:** `roles` (M:N via `user_roles`)

**Model file:** `models/admin_users.py`

---

### roles

Named groupings of permissions assigned to users.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated v4 |
| `role_name` | VARCHAR | NOT NULL, UNIQUE | e.g. "admin", "editor", "viewer" |
| `description` | VARCHAR | | Human-readable purpose |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Inactive roles are skipped during auth |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | | |
| `deleted_at` | TIMESTAMPTZ | | |

**Relationships:**
- `permissions` (M:N via `role_permissions`)
- `users` (M:N via `user_roles`)

**Model file:** `models/roles.py`

---

### resources

System entities that can be protected by permissions (e.g. "users", "reports", "settings").

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated v4 |
| `resource_name` | VARCHAR | NOT NULL, UNIQUE | e.g. "users", "reports", "settings" |
| `description` | VARCHAR | | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | | |
| `deleted_at` | TIMESTAMPTZ | | |

**Relationships:** `permissions` (one-to-many back to `permissions`)

**Model file:** `models/resources.py`

---

### permissions

An atomic capability: one action on one resource.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | Auto-generated v4 |
| `action` | ENUM(`action_type_enum`) | NOT NULL | CREATE, READ, UPDATE, DELETE, MANAGE |
| `resource_id` | UUID | FK -> resources.id, NOT NULL | CASCADE on delete |
| `description` | VARCHAR | | Auto or manual, e.g. "Can create users" |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | | |
| `deleted_at` | TIMESTAMPTZ | | |

**Constraints:** `UNIQUE(action, resource_id)` — prevents duplicate action-resource pairs.

**Relationships:**
- `resource` (many-to-one FK to `resources`)
- `roles` (M:N via `role_permissions`)

**Model file:** `models/permission.py`

---

### user_roles (junction)

Associates users with roles. Composite primary key.

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | PK, FK -> admin_users.id, CASCADE |
| `role_id` | UUID | PK, FK -> roles.id, CASCADE |

**Model file:** `models/associations.py`

---

### role_permissions (junction)

Associates roles with permissions. Composite primary key.

| Column | Type | Constraints |
|---|---|---|
| `role_id` | UUID | PK, FK -> roles.id, CASCADE |
| `permission_id` | UUID | PK, FK -> permissions.id, CASCADE |

**Model file:** `models/associations.py`

---

## ActionType Enum Values

| Value | Meaning |
|---|---|
| `CREATE` | Can create new instances of the resource |
| `READ` | Can view / list instances of the resource |
| `UPDATE` | Can modify existing instances of the resource |
| `DELETE` | Can remove instances of the resource |
| `MANAGE` | Full control — implies all actions on the resource |

Defined in: `models/permission.py` as `ActionType(str, Enum)`

---

## Shared Mixins

All entity tables inherit from these mixins (defined in `models/mixings.py`):

| Mixin | Columns Added | Purpose |
|---|---|---|
| `UUIDMix` | `id` (UUID, PK) | UUID v4 primary key |
| `TimeTrackingMix` | `created_at`, `updated_at` | Automatic timestamp tracking |
| `DeleteTrackingMix` | `deleted_at` + `soft_delete()` | Soft delete support |

---

## Example Data

### Resources

| resource_name | description |
|---|---|
| users | User management |
| roles | Role management |
| reports | Report generation and viewing |
| settings | Application configuration |

### Permissions

| action | resource | description |
|---|---|---|
| CREATE | users | Can create new users |
| READ | users | Can view user list and details |
| UPDATE | users | Can edit user profiles |
| DELETE | users | Can remove users |
| MANAGE | users | Full control over users |
| READ | reports | Can view reports |
| CREATE | reports | Can generate new reports |
| UPDATE | settings | Can modify app settings |

### Roles

| role_name | permissions |
|---|---|
| super_admin | users:MANAGE, roles:MANAGE, reports:MANAGE, settings:MANAGE |
| user_manager | users:CREATE, users:READ, users:UPDATE, users:DELETE |
| editor | reports:CREATE, reports:READ, reports:UPDATE |
| viewer | users:READ, reports:READ |

### User-Role Assignments

| user | roles |
|---|---|
| admin@telltake.com | super_admin |
| john@telltake.com | user_manager, editor |
| jane@telltake.com | viewer |

---

## File Structure

```
models/
├── __init__.py          # Central exports for all models
├── base.py              # SQLAlchemy declarative Base
├── mixings.py           # Shared mixins (UUID, timestamps, soft delete)
├── associations.py      # Junction tables (user_roles, role_permissions)
├── admin_users.py       # AdminUser model
├── roles.py             # Role model
├── resources.py         # Resource model
└── permission.py        # Permission model + ActionType enum
```

---

## Authorization Check (Pseudocode)

```python
def has_permission(user: AdminUser, action: ActionType, resource_name: str) -> bool:
    """Check if a user has a specific permission."""
    if user.is_superuser:
        return True

    if not user.is_active:
        return False

    for role in user.roles:
        if not role.is_active:
            continue
        for perm in role.permissions:
            if perm.resource.resource_name != resource_name:
                continue
            if perm.action == ActionType.MANAGE or perm.action == action:
                return True

    return False


# Usage
if has_permission(current_user, ActionType.UPDATE, "reports"):
    # allow the operation
    ...
```
