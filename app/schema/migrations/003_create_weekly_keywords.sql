CREATE TABLE IF NOT EXISTS `weekly_keywords`(
    `team_id` INTEGER NOT NULL, 
    `week_start` DATE NOT NULL, 
    `week_end` DATE NOT NULL,   
    `cluster_id` INTEGER NOT NULL, 
    `keyword` VARCHAR(255) NOT NULL,
    `score`FLOAT NOT NULL, 

    PRIMARY KEY (`team_id`, `week_start`, `week_end`, `cluster_id`, `keyword`),
    FOREIGN KEY (`team_id`, `week_start`, `week_end`, `cluster_id`)
        REFERENCES `weekly_clusters`(`team_id`, `week_start`, `week_end`, `cluster_id`)
        ON DELETE CASCADE
);