-- Schema v1.2 → v1.3 (Competitors page, competitors-spec)
-- Everything Instagram Business Discovery returns for a public Business/Creator account.
-- Run once on an existing database:  mysql -u root -p creatorly < db/migrations/2026-11-14_competitors.sql

ALTER TABLE competitors
  ADD COLUMN biography           TEXT          NULL AFTER name,
  ADD COLUMN website             VARCHAR(255)  NULL AFTER biography,
  ADD COLUMN profile_picture_url VARCHAR(1024) NULL AFTER website,
  ADD COLUMN last_synced_at      DATETIME      NULL AFTER added_at,
  ADD COLUMN sync_error          VARCHAR(255)  NULL AFTER last_synced_at;

ALTER TABLE competitor_daily_stats
  ADD COLUMN follows_count INT UNSIGNED NULL AFTER followers;

-- like_count is missing when the owner hides likes → NULL; view_count may be missing → NULL
ALTER TABLE competitor_posts
  MODIFY COLUMN likes INT UNSIGNED NULL,
  ADD COLUMN views         INT UNSIGNED  NULL AFTER comments,
  ADD COLUMN media_url     VARCHAR(1024) NULL AFTER permalink,
  ADD COLUMN thumbnail_url VARCHAR(1024) NULL AFTER media_url;

-- The same public account can be tracked by many users → a media id is unique per competitor row
ALTER TABLE competitor_posts
  DROP INDEX ig_media_id,
  ADD UNIQUE KEY uq_comp_media (competitor_id, ig_media_id);
