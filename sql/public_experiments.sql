-- phpMyAdmin SQL Dump
-- version 2.11.8.1deb5+lenny6
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Sep 29, 2010 at 03:37 PM
-- Server version: 5.0.51
-- PHP Version: 5.2.6-1+lenny9

SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

--
-- Database: `mash`
--


INSERT INTO experiments_configuration (id, name, heuristics, experiment_type, task) VALUES (39, "template/public/classification/perceptron-caltech-256", "LIST", "PUBL", "CLAS");
INSERT INTO experiments_configuration (id, name, heuristics, experiment_type, task) VALUES (40, "template/public/classification/adaboost-coil-100", "LIST", "PUBL", "CLAS");


--
-- Dumping data for table `experiments_setting`
--

INSERT INTO `experiments_setting` (`name`, `value`, `configuration_id`) VALUES
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 39),
('EXPERIMENT_SETUP/DATABASE_NAME', 'caltech-256', 39),
('EXPERIMENT_SETUP/LABELS', '61 161', 39),
('EXPERIMENT_SETUP/ROI_SIZE', '127', 39),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 39),
('USE_PREDICTOR', 'cdubout/perceptron', 39);


INSERT INTO `experiments_setting` (`name`, `value`, `configuration_id`) VALUES
('EXPERIMENT_SETUP/TRAINING_SAMPLES', '0.5', 40),
('EXPERIMENT_SETUP/DATABASE_NAME', 'coil-100', 40),
('EXPERIMENT_SETUP/LABELS', '20 22', 40),
('EXPERIMENT_SETUP/ROI_SIZE', '100', 40),
('EXPERIMENT_SETUP/BACKGROUND_IMAGES', 'OFF', 40),
('USE_PREDICTOR', 'cdubout/adaboost', 40);
