# NEXUS AI - Database Documentation

## Overview
NEXUS AI utilizes PostgreSQL as its primary production relational database engine. The data model is architected around UUID primary keys, relational integrity (foreign keys with cascade rules), indexing on critical query paths, and automatic audit timestamps (`created_at` and `updated_at`).

Migrations are managed deterministically using **Alembic**.

---

## Entity Relationship Diagram (ERD)

```
 +------------------------+             1:1             +------------------------+
 |         users          |-----------------------------|        profiles        |
 +------------------------+                             +------------------------+
 | PK id (UUID)           |                             | PK id (UUID)           |
 |    email (VARCHAR 255) |                             | FK user_id (UUID)      |
 |    username (VARCHAR)  |                             |    full_name (VARCHAR) |
 |    hashed_password     |                             |    bio (TEXT)          |
 |    is_active (BOOLEAN) |                             |    preferences (JSON)  |
 |    created_at (TIMEST) |                             |    created_at (TIMEST) |
 |    updated_at (TIMEST) |                             |    updated_at (TIMEST) |
 +------------------------+                             +------------------------+
        |            |
        | 1:N        | 1:N
        |            +-----------------------+
        v                                    v
 +------------------------+       1:N   +------------------------+
 |        projects        |------------>|         tasks          |
 +------------------------+             +------------------------+
 | PK id (UUID)           |             | PK id (UUID)           |
 | FK user_id (UUID)      |             | FK user_id (UUID)      |
 |    name (VARCHAR 200)  |             | FK project_id (UUID)   |
 |    description (TEXT)  |             |    title (VARCHAR 255) |
 |    status (VARCHAR 50) |             |    description (TEXT)  |
 |    start_date (DATE)   |             |    status (VARCHAR 50) |
 |    end_date (DATE)     |             |    priority (VARCHAR)  |
 |    created_at (TIMEST) |             |    due_date (DATE)     |
 |    updated_at (TIMEST) |             |    completed_at        |
 +------------------------+             |    created_at (TIMEST) |
                                        |    updated_at (TIMEST) |
        |                               +------------------------+
        | 1:N
        v
 +------------------------+
 |         goals          |
 +------------------------+
 | PK id (UUID)           |
 | FK user_id (UUID)      |
 |    title (VARCHAR 255) |
 |    description (TEXT)  |
 |    category (VARCHAR)  |
 |    status (VARCHAR 50) |
 |    progress_pct (INT)  |
 |    target_date (DATE)  |
 |    created_at (TIMEST) |
 |    updated_at (TIMEST) |
 +------------------------+
```

---

## Tables Specification

### 1. `users`
Represents system accounts and primary authentication credentials.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, INDEX | Unique user identifier (UUID v4) |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE, INDEX | User login email address |
| `username` | VARCHAR(50) | UNIQUE, INDEX, NULLABLE | Optional unique username |
| `hashed_password` | VARCHAR(255) | NOT NULL | Bcrypt password hash |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Account status flag |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Last modified timestamp |

### 2. `profiles`
User metadata, personal bio, and application preferences.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, INDEX | Unique profile identifier |
| `user_id` | UUID | NOT NULL, UNIQUE, FK -> users.id (CASCADE) | Associated user reference |
| `full_name` | VARCHAR(100) | NULLABLE | Display name |
| `bio` | TEXT | NULLABLE | Biography / bio snippet |
| `preferences` | JSON | NOT NULL, DEFAULT `{}` | JSON configuration (theme, notifications) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Last modified timestamp |

### 3. `projects`
Workspaces and project containers owned by users.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, INDEX | Unique project identifier |
| `user_id` | UUID | NOT NULL, INDEX, FK -> users.id (CASCADE) | Owner user ID |
| `name` | VARCHAR(200) | NOT NULL, INDEX | Project title |
| `description` | TEXT | NULLABLE | Project description |
| `status` | VARCHAR(50) | NOT NULL, INDEX, DEFAULT 'active' | Status: `active`, `completed`, `archived`, `on_hold` |
| `start_date` | DATE | NULLABLE | Estimated or actual start date |
| `end_date` | DATE | NULLABLE | Target delivery date |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Last modified timestamp |

### 4. `tasks`
Individual actionable items with priorities, deadlines, and optional project association.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, INDEX | Unique task identifier |
| `user_id` | UUID | NOT NULL, INDEX, FK -> users.id (CASCADE) | Task owner user ID |
| `project_id` | UUID | NULLABLE, INDEX, FK -> projects.id (SET NULL) | Linked project (optional) |
| `title` | VARCHAR(255) | NOT NULL, INDEX | Task title |
| `description` | TEXT | NULLABLE | Detailed description |
| `status` | VARCHAR(50) | NOT NULL, INDEX, DEFAULT 'todo' | Status: `todo`, `in_progress`, `completed`, `blocked` |
| `priority` | VARCHAR(20) | NOT NULL, INDEX, DEFAULT 'medium' | Priority: `low`, `medium`, `high`, `urgent` |
| `due_date` | DATE | NULLABLE, INDEX | Target completion date |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Timestamp when marked completed |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Last modified timestamp |

### 5. `goals`
High-level strategic targets with category classification and percentage progress tracking.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, INDEX | Unique goal identifier |
| `user_id` | UUID | NOT NULL, INDEX, FK -> users.id (CASCADE) | Goal owner user ID |
| `title` | VARCHAR(255) | NOT NULL, INDEX | Goal title |
| `description` | TEXT | NULLABLE | Long-form details |
| `category` | VARCHAR(50) | NOT NULL, INDEX, DEFAULT 'personal' | Category: `career`, `learning`, `personal`, `fitness`, `financial` |
| `status` | VARCHAR(50) | NOT NULL, INDEX, DEFAULT 'active' | Status: `active`, `completed`, `on_hold`, `cancelled` |
| `progress_pct` | INTEGER | NOT NULL, DEFAULT 0, CHECK (0 <= x <= 100) | Numerical progress percentage (0 - 100) |
| `target_date` | DATE | NULLABLE, INDEX | Target attainment date |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT utcnow | Last modified timestamp |

---

## Migrations Guide

Alembic configuration is situated in `backend/alembic.ini` and `backend/alembic/`.

### Running Migrations
To upgrade the database to the latest schema version:
```bash
cd backend
alembic upgrade head
```

### Creating New Migrations
When adding new models or schema changes in future phases:
```bash
cd backend
alembic revision --autogenerate -m "describe_change"
```
