
"""Database schema definitions for TimanStat."""

from __future__ import annotations


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
            CHECK (role IN ('super_admin', 'admin', 'developer', 'user')),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        email_verified BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS organisations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        organisation_type TEXT,
        registration_number TEXT,
        contact_email TEXT,
        country TEXT,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'suspended', 'closed')),
        created_by TEXT REFERENCES users(id),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS organisation_memberships (
        id TEXT PRIMARY KEY,
        organisation_id TEXT NOT NULL
            REFERENCES organisations(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL
            REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'org_member'
            CHECK (role IN ('org_admin', 'org_member')),
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'pending', 'suspended')),
        joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (organisation_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        organisation_id TEXT NOT NULL
            REFERENCES organisations(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'on_hold', 'completed', 'archived')),
        created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_memberships (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL
            REFERENCES projects(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL
            REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'project_member'
            CHECK (role IN ('project_admin', 'project_member')),
        status TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'pending', 'suspended')),
        joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (project_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
        organisation_id TEXT
            REFERENCES organisations(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        resource_type TEXT,
        resource_id TEXT,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_memberships_user
    ON organisation_memberships(user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_memberships_organisation
    ON organisation_memberships(organisation_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_projects_organisation
    ON projects(organisation_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_project_memberships_user
    ON project_memberships(user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_project_memberships_project
    ON project_memberships(project_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_user
    ON audit_logs(user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_audit_created
    ON audit_logs(created_at)
    """,
]
