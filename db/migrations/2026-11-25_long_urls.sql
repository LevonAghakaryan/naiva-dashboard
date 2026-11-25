-- Instagram CDN URLs (reels media_url etc.) can exceed 1024 chars -> VARCHAR(1024) to TEXT.
-- Run once on an existing database:  mysql -u root -p creatorly < db/migrations/2026-11-25_long_urls.sql

ALTER TABLE competitor_posts MODIFY media_url TEXT NULL, MODIFY thumbnail_url TEXT NULL;
ALTER TABLE competitors      MODIFY profile_picture_url TEXT NULL;
ALTER TABLE posts            MODIFY thumbnail_url TEXT NULL;
ALTER TABLE ig_accounts      MODIFY profile_pic_url TEXT NULL;
