# NEXUS AI - API Reference (Phase 1)

## Overview
The NEXUS AI Phase 1 REST API is built on FastAPI and OpenAPI standards. All data payloads are serialized in JSON format. Interactive Swagger documentation is available at `/docs` and ReDoc at `/redoc`.

Base URL: `http://localhost:8000` (or `/api/v1`)

---

## Authentication & Headers
Protected endpoints require an HTTP Authorization header formatted as:
```http
Authorization: Bearer <your_jwt_access_token>
```

---

## Endpoints Summary

### 1. Authentication

#### Register a New User
- **Method & Path**: `POST /auth/register` (also `/api/v1/auth/register`)
- **Status Code**: `201 Created`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "username": "alex"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "c7a8b412-f19c-4c6e-82d1-0f7e44a90401",
      "email": "user@example.com",
      "username": "alex",
      "is_active": true,
      "created_at": "2026-10-13T12:00:00Z",
      "updated_at": "2026-10-13T12:00:00Z",
      "profile": {
        "id": "e2d8b512-...",
        "user_id": "c7a8b412-...",
        "full_name": "alex",
        "bio": "",
        "preferences": { "theme": "dark", "notifications_enabled": true },
        "created_at": "2026-10-13T12:00:00Z",
        "updated_at": "2026-10-13T12:00:00Z"
      }
    }
  }
  ```

#### Login
- **Method & Path**: `POST /auth/login` (also `/api/v1/auth/login`)
- **Status Code**: `200 OK`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response**: Returns JWT bearer `access_token` and `user` payload.

---

### 2. Users & Profile

#### Get Current User Info
- **Method & Path**: `GET /users/me` (also `/api/v1/users/me`)
- **Auth Required**: Yes
- **Response**: Current user record and nested profile.

#### Update Profile
- **Method & Path**: `PATCH /users/me/profile` (also `/api/v1/users/me/profile`)
- **Auth Required**: Yes
- **Request Body**:
  ```json
  {
    "full_name": "Alex Mercer",
    "bio": "AI Researcher & Architect",
    "preferences": {
      "theme": "dark",
      "notifications_enabled": true
    }
  }
  ```
- **Response**: Updated profile object.

---

### 3. Projects

#### List Projects
- **Method & Path**: `GET /projects` (also `/api/v1/projects`)
- **Query Params**: `status_filter` (optional: `active`, `completed`, `archived`, `on_hold`)
- **Response**: List of project objects owned by current user.

#### Create Project
- **Method & Path**: `POST /projects`
- **Status Code**: `201 Created`
- **Request Body**:
  ```json
  {
    "name": "NEXUS Core Engine",
    "description": "Production foundational intelligence service",
    "status": "active",
    "start_date": "2026-10-01",
    "end_date": "2026-11-30"
  }
  ```

#### Get Project by ID
- **Method & Path**: `GET /projects/{project_id}`
- **Response**: Project object (or `404 Not Found` if not owned).

#### Update Project
- **Method & Path**: `PATCH /projects/{project_id}`
- **Request Body**: Any partial fields (`name`, `description`, `status`, `start_date`, `end_date`).

#### Delete Project
- **Method & Path**: `DELETE /projects/{project_id}`
- **Status Code**: `204 No Content`

---

### 4. Tasks

#### List Tasks
- **Method & Path**: `GET /tasks`
- **Query Params**: `project_id`, `status_filter` (`todo`, `in_progress`, `completed`, `blocked`), `priority_filter` (`low`, `medium`, `high`, `urgent`)
- **Response**: List of task objects owned by current user.

#### Create Task
- **Method & Path**: `POST /tasks`
- **Status Code**: `201 Created`
- **Request Body**:
  ```json
  {
    "title": "Build user auth modules",
    "description": "Implement bcrypt hashing & JWT tokens",
    "project_id": "c7a8b412-f19c-4c6e-82d1-0f7e44a90401",
    "status": "todo",
    "priority": "high",
    "due_date": "2026-10-20"
  }
  ```

#### Get Task by ID
- **Method & Path**: `GET /tasks/{task_id}`

#### Update Task
- **Method & Path**: `PATCH /tasks/{task_id}`
- **Request Body**: Partial fields (`title`, `description`, `project_id`, `status`, `priority`, `due_date`).

#### Delete Task
- **Method & Path**: `DELETE /tasks/{task_id}`
- **Status Code**: `204 No Content`

---

### 5. Goals

#### List Goals
- **Method & Path**: `GET /goals`
- **Query Params**: `category`, `status_filter`
- **Response**: List of goal objects owned by current user.

#### Create Goal
- **Method & Path**: `POST /goals`
- **Status Code**: `201 Created`
- **Request Body**:
  ```json
  {
    "title": "Master Agentic AI System Architecture",
    "description": "Deep-dive into multi-agent protocols and memory graphs",
    "category": "learning",
    "status": "active",
    "progress_pct": 35,
    "target_date": "2026-12-31"
  }
  ```

#### Get Goal by ID
- **Method & Path**: `GET /goals/{goal_id}`

#### Update Goal
- **Method & Path**: `PATCH /goals/{goal_id}`
- **Request Body**: Partial fields (`title`, `description`, `category`, `status`, `progress_pct`, `target_date`).

#### Delete Goal
- **Method & Path**: `DELETE /goals/{goal_id}`
- **Status Code**: `204 No Content`

---

### 6. Dashboard

#### Get Dashboard Overview
- **Method & Path**: `GET /dashboard/overview` (also `/api/v1/dashboard/overview`)
- **Auth Required**: Yes
- **Response**:
  ```json
  {
    "stats": {
      "total_tasks": 12,
      "completed_tasks": 7,
      "pending_tasks": 5,
      "in_progress_tasks": 2,
      "completion_rate": 58.3,
      "active_projects_count": 3,
      "active_goals_count": 2,
      "average_goal_progress": 62.5
    },
    "todays_tasks": [...],
    "upcoming_tasks": [...],
    "active_projects": [...],
    "active_goals": [...]
  }
  ```
