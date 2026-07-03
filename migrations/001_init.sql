CREATE TABLE IF NOT EXISTS tickets (
  id SERIAL PRIMARY KEY,
  external_ref VARCHAR(80) UNIQUE,
  requester_name VARCHAR(120) NOT NULL,
  requester_email VARCHAR(160) NOT NULL,
  channel VARCHAR(40) NOT NULL,
  subject VARCHAR(160) NOT NULL,
  message TEXT NOT NULL,
  priority VARCHAR(20) NOT NULL DEFAULT 'normal',
  status VARCHAR(40) NOT NULL DEFAULT 'new',
  assignee VARCHAR(120),
  sla_due_at TIMESTAMPTZ NOT NULL,
  sla_breached BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS ix_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS ix_tickets_sla_breached ON tickets(sla_breached);
CREATE INDEX IF NOT EXISTS ix_tickets_requester_email ON tickets(requester_email);

CREATE TABLE IF NOT EXISTS activity_logs (
  id SERIAL PRIMARY KEY,
  ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  event_type VARCHAR(80) NOT NULL,
  actor VARCHAR(120) NOT NULL DEFAULT 'system',
  note TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_activity_logs_ticket_id ON activity_logs(ticket_id);
CREATE INDEX IF NOT EXISTS ix_activity_logs_event_type ON activity_logs(event_type);
