-- Schéma initial de Gotcha (PostgreSQL 14 ou plus). Responsable : Abdoul Aziz.
-- Les fiches et pièges sont stockés en JSONB (le modèle Pydantic sérialisé, décision
-- D6), avec quelques colonnes extraites pour filtrer et compter les confirmations.
-- La recherche se fait dans l'application, comme pour le stockage mémoire (D17).
-- Une migration appliquée ne se modifie plus : on en ajoute une nouvelle (002_…).

CREATE TABLE fiches (
    slug               text PRIMARY KEY,
    service_slug       text        NOT NULL,
    country            char(2),
    publication        text        NOT NULL CHECK (publication IN ('draft', 'published')),
    title              text        NOT NULL,
    data               jsonb       NOT NULL,  -- modèle Fiche, sans ses pièges
    last_confirmed_on  date        NOT NULL,
    confirmations      integer     NOT NULL DEFAULT 0,
    updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX fiches_service_idx ON fiches (service_slug, country);

CREATE TABLE gotchas (
    id                 text PRIMARY KEY,      -- "<slug de la fiche>.<nom du fichier>"
    fiche_slug         text        NOT NULL REFERENCES fiches (slug) ON DELETE CASCADE,
    position           integer     NOT NULL,  -- ordre du piège dans sa fiche
    publication        text        NOT NULL CHECK (publication IN ('draft', 'published')),
    data               jsonb       NOT NULL,  -- modèle Gotcha
    last_confirmed_on  date        NOT NULL,
    confirmations      integer     NOT NULL DEFAULT 0,
    updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX gotchas_fiche_idx ON gotchas (fiche_slug, position);

-- Historique des versions du contenu d'une fiche (une ligne quand le contenu change).
CREATE TABLE fiche_revisions (
    id          bigserial PRIMARY KEY,
    fiche_slug  text        NOT NULL REFERENCES fiches (slug) ON DELETE CASCADE,
    data        jsonb       NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE glossary_terms (
    slug        text PRIMARY KEY,
    term        text NOT NULL,
    definition  text NOT NULL
);

CREATE TABLE confirmations (
    id           bigserial PRIMARY KEY,
    target_kind  text        NOT NULL CHECK (target_kind IN ('fiche', 'gotcha')),
    target_id    text        NOT NULL,
    still_works  boolean     NOT NULL DEFAULT true,
    api_version  text,
    pseudo       text,
    created_at   timestamptz NOT NULL
);
CREATE INDEX confirmations_target_idx ON confirmations (target_kind, target_id);

CREATE TABLE contributions (
    id           text PRIMARY KEY,
    kind         text        NOT NULL CHECK (kind IN ('gotcha', 'step', 'correction')),
    fiche_slug   text        NOT NULL,
    title        text        NOT NULL,
    body_md      text        NOT NULL,
    source_url   text,
    api_version  text,
    pseudo       text        NOT NULL,
    email        text        NOT NULL,  -- donnée personnelle : jamais exposée
    status       text        NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at   timestamptz NOT NULL,
    reviewed_at  timestamptz,
    reviewer     text,
    review_note  text
);
CREATE INDEX contributions_queue_idx ON contributions (status, created_at);

CREATE TABLE incidents (
    id            text PRIMARY KEY,
    source        text        NOT NULL CHECK (source IN ('flutterwave', 'community', 'agent')),
    external_id   text,
    service_slug  text,
    country       char(2),
    status        text        NOT NULL CHECK (status IN ('normal', 'degraded', 'down', 'unknown')),
    title         text        NOT NULL,
    description   text,
    url           text,
    started_at    timestamptz NOT NULL,
    resolved_at   timestamptz,
    reported_by   text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX incidents_recent_idx ON incidents (started_at DESC);
CREATE INDEX incidents_active_idx ON incidents (started_at DESC) WHERE resolved_at IS NULL;

CREATE TABLE ingest_runs (
    source           text PRIMARY KEY,
    last_success_at  timestamptz NOT NULL
);
