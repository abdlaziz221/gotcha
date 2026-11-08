-- Comptes des développeurs et données de connexion OAuth du serveur MCP (D20).
-- Les jetons et les codes ne sont jamais stockés : seulement leur empreinte SHA-256.

CREATE TABLE accounts (
    id             text PRIMARY KEY,
    pseudo         text        NOT NULL,
    created_at     timestamptz NOT NULL,
    last_login_at  timestamptz NOT NULL,
    blocked        boolean     NOT NULL DEFAULT false
);

CREATE TABLE oauth_clients (
    client_id   text PRIMARY KEY,
    data        jsonb       NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE oauth_grants (
    kind        text        NOT NULL CHECK (kind IN ('login', 'code', 'access', 'refresh')),
    key_hash    text        NOT NULL,
    data        jsonb       NOT NULL,
    expires_at  timestamptz NOT NULL,
    PRIMARY KEY (kind, key_hash)
);
CREATE INDEX oauth_grants_expiry_idx ON oauth_grants (expires_at);
