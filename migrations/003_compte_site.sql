-- Connexion sur le site : sessions, contributions et confirmations liées à un compte (D23).

ALTER TABLE oauth_grants DROP CONSTRAINT oauth_grants_kind_check;
ALTER TABLE oauth_grants ADD CONSTRAINT oauth_grants_kind_check
    CHECK (kind IN ('login', 'code', 'access', 'refresh', 'session'));

ALTER TABLE contributions ALTER COLUMN email DROP NOT NULL;
ALTER TABLE contributions ADD COLUMN account_id text;

ALTER TABLE confirmations ADD COLUMN account_id text;
ALTER TABLE confirmations ADD COLUMN proof text;
CREATE INDEX confirmations_account_idx ON confirmations (account_id, target_id, created_at)
    WHERE account_id IS NOT NULL;
