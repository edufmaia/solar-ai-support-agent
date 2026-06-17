-- =========================================================
-- Solar AI Support Agent
-- T004 — Initial PostgreSQL schema
-- =========================================================
-- Scope:
-- - leads
-- - conversations
-- - messages
-- - agent_events
-- - geospatial_analysis
-- - model_costs
-- - knowledge_documents
--
-- Notes:
-- - Script is idempotent where possible using IF NOT EXISTS.
-- - IDs use pgcrypto/gen_random_uuid().
-- - No application-side integration is required for this schema.
-- =========================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 1) Leads
-- =========================================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    phone TEXT,
    email TEXT,
    city TEXT,
    state TEXT,
    address TEXT,
    property_type TEXT,
    average_energy_bill NUMERIC(10, 2) CHECK (average_energy_bill IS NULL OR average_energy_bill >= 0),
    intent TEXT,
    lead_score INTEGER CHECK (lead_score IS NULL OR lead_score BETWEEN 0 AND 100),
    lead_temperature TEXT CHECK (lead_temperature IS NULL OR lead_temperature IN ('cold', 'warm', 'hot')),
    status TEXT CHECK (
        status IS NULL OR status IN (
            'new',
            'in_progress',
            'qualified',
            'handoff_requested',
            'converted',
            'lost',
            'archived'
        )
    ),
    source_channel TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads (phone);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads (email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_temperature ON leads (lead_temperature);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at DESC);

-- =========================================================
-- 2) Conversations
-- =========================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NULL REFERENCES leads(id) ON DELETE SET NULL,
    channel TEXT,
    status TEXT CHECK (
        status IS NULL OR status IN (
            'active',
            'waiting_user',
            'waiting_human',
            'closed',
            'failed'
        )
    ),
    current_state TEXT,
    assigned_to_human BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ NULL
);

ALTER TABLE conversations
    DROP CONSTRAINT IF EXISTS conversations_status_check;

ALTER TABLE conversations
    ADD CONSTRAINT conversations_status_check
    CHECK (
        status IS NULL OR status IN (
            'open',
            'active',
            'waiting_user',
            'waiting_human',
            'closed',
            'failed'
        )
    );

CREATE INDEX IF NOT EXISTS idx_conversations_lead_id ON conversations (lead_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations (channel);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at DESC);

-- =========================================================
-- 3) Messages
-- =========================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    model_provider TEXT,
    model_name TEXT,
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    estimated_cost NUMERIC(12, 6) CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created_at ON messages (conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages (role);

-- =========================================================
-- 4) Agent events
-- =========================================================
CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    lead_id UUID NULL REFERENCES leads(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_source TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_conversation_id ON agent_events (conversation_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_lead_id ON agent_events (lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events (event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_created_at ON agent_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_payload_gin ON agent_events USING GIN (payload);

-- =========================================================
-- 5) Geospatial analysis
-- =========================================================
CREATE TABLE IF NOT EXISTS geospatial_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    conversation_id UUID NULL REFERENCES conversations(id) ON DELETE SET NULL,
    raw_address TEXT,
    formatted_address TEXT,
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    address_confidence TEXT CHECK (
        address_confidence IS NULL OR address_confidence IN ('low', 'medium', 'high', 'unknown')
    ),
    solar_data_available BOOLEAN NOT NULL DEFAULT FALSE,
    estimated_panel_min INTEGER CHECK (estimated_panel_min IS NULL OR estimated_panel_min >= 0),
    estimated_panel_max INTEGER CHECK (estimated_panel_max IS NULL OR estimated_panel_max >= 0),
    estimated_system_kwp NUMERIC(10, 2) CHECK (estimated_system_kwp IS NULL OR estimated_system_kwp >= 0),
    confidence_level TEXT CHECK (
        confidence_level IS NULL OR confidence_level IN ('low', 'medium', 'high', 'unknown')
    ),
    requires_technical_review BOOLEAN NOT NULL DEFAULT FALSE,
    raw_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        estimated_panel_min IS NULL
        OR estimated_panel_max IS NULL
        OR estimated_panel_min <= estimated_panel_max
    )
);

CREATE INDEX IF NOT EXISTS idx_geospatial_analysis_lead_id ON geospatial_analysis (lead_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_analysis_conversation_id ON geospatial_analysis (conversation_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_analysis_created_at ON geospatial_analysis (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_geospatial_analysis_solar_data_available ON geospatial_analysis (solar_data_available);

-- =========================================================
-- 6) Model costs
-- =========================================================
CREATE TABLE IF NOT EXISTS model_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID NULL REFERENCES messages(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
    estimated_cost NUMERIC(12, 6) CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_costs_conversation_id ON model_costs (conversation_id);
CREATE INDEX IF NOT EXISTS idx_model_costs_message_id ON model_costs (message_id);
CREATE INDEX IF NOT EXISTS idx_model_costs_provider_model ON model_costs (provider, model_name);
CREATE INDEX IF NOT EXISTS idx_model_costs_created_at ON model_costs (created_at DESC);

-- =========================================================
-- 7) Knowledge documents
-- =========================================================
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    category TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_active ON knowledge_documents (is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_category ON knowledge_documents (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_active_category ON knowledge_documents (is_active, category);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_search
    ON knowledge_documents
    USING GIN (to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(content, '')));
