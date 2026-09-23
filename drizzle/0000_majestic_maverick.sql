CREATE TABLE `access_tokens` (
	`token_hash` text PRIMARY KEY NOT NULL,
	`subject` text NOT NULL,
	`expires` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `audit_events` (
	`id` text PRIMARY KEY NOT NULL,
	`subject` text NOT NULL,
	`created_at` text NOT NULL,
	`person_id` text NOT NULL,
	`route` text NOT NULL,
	`purpose` text NOT NULL,
	`action` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_audit_subject_created` ON `audit_events` (`subject`,`created_at`);--> statement-breakpoint
CREATE TABLE `care_contacts` (
	`person_id` text PRIMARY KEY NOT NULL,
	`contacted` integer DEFAULT 0 NOT NULL,
	`updated_at` text NOT NULL,
	`subject` text NOT NULL
);
