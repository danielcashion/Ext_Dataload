DROP TABLE IF EXISTS system_jobs;

CREATE TABLE IF NOT EXISTS system_jobs (
  job_id VARCHAR(80) NOT NULL,
  status TEXT NULL,
  `is_active_YN` TINYINT NOT NULL DEFAULT 1,
  `created_by` VARCHAR(8) NOT NULL DEFAULT 1,
  `created_datetime` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_by` VARCHAR(8) NULL,
  `updated_datetime` DATETIME NULL,
  PRIMARY KEY (`job_id`))
ENGINE = InnoDB;

INSERT INTO apiconfig (resource, tablename, primary_key, search_fields, sort_fields, read_access, write_access, is_auditable)  
VALUES ("system_jobs", "system_jobs", "job_id", "job_id status is_active_YN is_published_YN created_by created_datetime updated_by updated_datetime", "", "ALL", "ALL", 0);
