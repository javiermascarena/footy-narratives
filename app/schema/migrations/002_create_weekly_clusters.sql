CREATE TABLE IF NOT EXISTS `weekly_clusters` ( 
    `team_id` INT NOT NULL, 
    `week_start` DATE NOT NULL, 
    `week_end` DATE NOT NULL, 
    `cluster_id` INT NOT NULL, 
    size INT DEFAULT 0, 
    PRIMARY KEY (`team_id`, `week_start`, `week_end`, `cluster_id`),
    FOREIGN KEY (`team_id`) REFERENCES `teams`(`id`)
);