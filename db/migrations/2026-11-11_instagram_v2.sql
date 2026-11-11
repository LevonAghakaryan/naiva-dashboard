-- Schema v1.1 → v1.2 (Instagram analytics v2, instagram-spec.md)
-- Run once on an existing database:  mysql -u root -p creatorly < db/migrations/2026-11-11_instagram_v2.sql

ALTER TABLE account_daily_stats
  ADD COLUMN new_follows        INT UNSIGNED NOT NULL DEFAULT 0 AFTER followers,
  ADD COLUMN unfollows          INT UNSIGNED NOT NULL DEFAULT 0 AFTER new_follows,
  ADD COLUMN non_follower_reach INT UNSIGNED NOT NULL DEFAULT 0 AFTER reach,
  ADD COLUMN accounts_engaged   INT UNSIGNED NOT NULL DEFAULT 0 AFTER views,
  ADD COLUMN interactions       INT UNSIGNED NOT NULL DEFAULT 0 AFTER accounts_engaged,
  ADD COLUMN likes              INT UNSIGNED NOT NULL DEFAULT 0 AFTER interactions,
  ADD COLUMN comments           INT UNSIGNED NOT NULL DEFAULT 0 AFTER likes,
  ADD COLUMN saves              INT UNSIGNED NOT NULL DEFAULT 0 AFTER comments,
  ADD COLUMN shares             INT UNSIGNED NOT NULL DEFAULT 0 AFTER saves,
  ADD COLUMN reposts            INT UNSIGNED NOT NULL DEFAULT 0 AFTER shares,
  ADD COLUMN link_taps          INT UNSIGNED NOT NULL DEFAULT 0 AFTER profile_views;

CREATE TABLE IF NOT EXISTS account_period_stats (
  id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ig_account_id      BIGINT UNSIGNED NOT NULL,
  end_day            DATE NOT NULL,
  days               TINYINT UNSIGNED NOT NULL,
  reach              INT UNSIGNED NOT NULL DEFAULT 0,
  non_follower_reach INT UNSIGNED NOT NULL DEFAULT 0,
  accounts_engaged   INT UNSIGNED NOT NULL DEFAULT 0,
  FOREIGN KEY (ig_account_id) REFERENCES ig_accounts(id) ON DELETE CASCADE,
  UNIQUE KEY uq_account_period (ig_account_id, end_day, days)
) ENGINE=InnoDB;

ALTER TABLE post_stats
  ADD COLUMN reposts INT UNSIGNED NOT NULL DEFAULT 0 AFTER shares,
  ADD COLUMN follows INT UNSIGNED NOT NULL DEFAULT 0 AFTER reposts;
