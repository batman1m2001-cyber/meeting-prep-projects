-- The brief's own stores, in their own schema: the optimized build's `public`
-- tables (CRM, calendar, knowledge base) are read, never written.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS brd;

-- Memory Agent: facts, past results and research history per company or user.
CREATE TABLE IF NOT EXISTS brd.memory_items (
    id          serial PRIMARY KEY,
    subject     text NOT NULL,                 -- a company id, or "user:<id>"
    kind        text NOT NULL,                 -- fact | result | note
    content     text NOT NULL,
    source      text,
    embedding   vector(1536),
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (subject, kind, content)
);

-- One row per research run: who, which sources, when.
CREATE TABLE IF NOT EXISTS brd.research_runs (
    id          serial PRIMARY KEY,
    company_id  text NOT NULL,
    email_id    text,
    summary     text,
    sources     jsonb NOT NULL DEFAULT '[]',
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- What sales wants from a brief.
CREATE TABLE IF NOT EXISTS brd.user_profile (
    user_id     text PRIMARY KEY,
    name        text NOT NULL,
    email       text NOT NULL,
    preferences jsonb NOT NULL
);

-- Report Generation Agent: each report and its formats.
CREATE TABLE IF NOT EXISTS brd.reports (
    id          serial PRIMARY KEY,
    company_id  text,
    title       text NOT NULL,
    markdown    text NOT NULL,
    email_body  text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Human Approval (a person): nothing important runs before its row says approved.
CREATE TABLE IF NOT EXISTS brd.approvals (
    id          serial PRIMARY KEY,
    task        text NOT NULL,
    payload     jsonb NOT NULL,
    status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    decided_by  text,
    decided_at  timestamptz
);

-- Save to KB: approved briefs (the CRM notes stay in public.kb_chunks).
CREATE TABLE IF NOT EXISTS brd.kb_chunks (
    id          serial PRIMARY KEY,
    company_id  text,
    source      text NOT NULL,
    content     text NOT NULL,
    embedding   vector(1536),
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Tool harness, step 5: every call, allowed or refused.
CREATE TABLE IF NOT EXISTS brd.audit (
    id          bigserial PRIMARY KEY,
    at          timestamptz NOT NULL DEFAULT now(),
    agent       text NOT NULL,
    tool        text NOT NULL,
    args        jsonb NOT NULL,
    verdict     text NOT NULL                  -- "allowed", or why it was refused
);
