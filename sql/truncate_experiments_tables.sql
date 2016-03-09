USE mash;

TRUNCATE TABLE servers_job;
TRUNCATE TABLE servers_alert;
TRUNCATE TABLE experiments_configuration;
TRUNCATE TABLE experiments_configuration_heuristics_set;
TRUNCATE TABLE experiments_experiment;
TRUNCATE TABLE experiments_heuristicrank;
TRUNCATE TABLE experiments_results;
TRUNCATE TABLE experiments_setting;

--
-- Dumping data for table `experiments_configuration`
--

INSERT INTO `experiments_configuration` (`id`, `name`, `heuristics`, `experiment_type`, `task`) VALUES
(1, 'template/classification', 'LIST', 'PRIV', 'CLAS'),
(2, 'template/classification', 'LVAH', 'CONS', 'CLAS');



--
-- Dumping data for table `experiments_setting`
--

INSERT INTO `experiments_setting` (`name`, `value`, `configuration_id`) VALUES
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 1),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 1),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 1),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 2),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 2),
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 2),
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 3),
('EXPERIMENT_SETUP/DATABASE_NAME', 'coil-100', 3),
('EXPERIMENT_SETUP/LABELS', '0 1', 3),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 3),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 3),
('USE_PREDICTOR', 'examples/dummy', 3),
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.2', 4),
('EXPERIMENT_SETUP/DATABASE_NAME', 'coil-100', 4),
('EXPERIMENT_SETUP/LABELS', '20 22', 4),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 4),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 4),
('USE_PREDICTOR', 'examples/advanced', 4),
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 5),
('EXPERIMENT_SETUP/DATABASE_NAME', 'caltech-256', 5),
('EXPERIMENT_SETUP/LABELS', '61 161', 5),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 5),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 5),
('USE_PREDICTOR', 'examples/dummy', 5);


INSERT INTO `experiments_configurationseed` (`configuration_id`, `conf_seed`) VALUES
(3, 2),
(3, 10),
(4, 10000),
(4, 12000),
(5, 356502),
(5, 500000);


