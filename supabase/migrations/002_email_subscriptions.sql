-- Email Subscriptions Table
-- For newsletter/alert signups before user authentication

CREATE TABLE IF NOT EXISTS email_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'website',  -- Where they signed up (website, api, etc.)
    is_active BOOLEAN DEFAULT TRUE,
    unsubscribed_at TIMESTAMPTZ
);

CREATE INDEX idx_email_subscriptions_email ON email_subscriptions(email);
CREATE INDEX idx_email_subscriptions_active ON email_subscriptions(is_active);

-- Enable RLS
ALTER TABLE email_subscriptions ENABLE ROW LEVEL SECURITY;

-- Allow public insert (anyone can subscribe)
CREATE POLICY "Anyone can subscribe" ON email_subscriptions
    FOR INSERT WITH CHECK (true);

-- Allow backend service role to read/update
CREATE POLICY "Service role full access" ON email_subscriptions
    FOR ALL USING (auth.role() = 'service_role');
