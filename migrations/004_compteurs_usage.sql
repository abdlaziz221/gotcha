-- Compteurs d'usage par jour et par compte (D24). Aucune requête ni contenu n'est conservé.

CREATE TABLE usage_counters (
    day         date    NOT NULL,
    event       text    NOT NULL,
    account_id  text    NOT NULL DEFAULT '',  -- vide : visiteur sans compte
    count       integer NOT NULL DEFAULT 0,
    PRIMARY KEY (day, event, account_id)
);
