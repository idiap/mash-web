--
-- Dumping data for table `django_site`
--

INSERT INTO `django_site` (`id`, `domain`, `name`) VALUES
(1, 'mash-project.eu', 'mash');


--
-- Dumping data for table `menu_menuitem`
--

INSERT INTO `menu_menuitem` (`id`, `label`, `link`, `index`, `display`) VALUES
(1, 'News', '/news', 0, 'ALWAYS'),
(2, 'Documentation', '/wiki', 10, 'ALWAYS'),
(3, 'Downloads', '/downloads', 20, 'ALWAYS'),
(4, 'Members', '/accounts/members', 30, 'ALWAYS'),
(5, 'Forum', '/forum', 40, 'ALWAYS'),
(6, 'Heuristics', '/heuristics', 50, 'ALWAYS'),
(7, 'Experiments', '/experiments', 60, 'ALWAYS');


--
-- Dumping data for table `texts_db_text`
--

INSERT INTO `texts_db_text` (`name`, `content`) VALUES
('HEURISTIC_UPLOAD_CONFIRMATION', '<p style="text-align: justify;">By uploading Material and Contributions on the MASH platform/website, you:
    <ul>
        <li>Grant the <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a> the right to compile it</li>
        <li>Link the resulting binary with other binary files and</li>
        <li>Run the resulting executable</li>
    </ul>
</p>

<p style="text-align: justify;">You also grant the <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a>
    the right to use the experimental results obtained by running this executable (error rates and various performance measures)
    without limit in time.</p>

<p>You are entitled, at any time, to ask <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a> 
   to delete the Material and Contributions from the servers. At that moment, you also remove the granting mentioned above.
   For technical reasons, <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a> is only able to
   remove information under its control and the deletion may take a reasonable period of time before being processed.
   You understand that the Material and Contributions will be deleted from everywhere
   <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a> is entitled and has access to.</p>
'),
('HEURISTIC_UPLOAD_CHOICE', 'You already have a heuristic with this name. Do you want to create a new heuristic with a different name or upload a new version of the existing heuristic?'),
('HEURISTIC_VERSION_DELETION_CONFIRMATION', '<p style="text-align: justify">You are about to delete this heuristic version. If you continue, <strong>you won''t be able to retrieve it!</strong></p>\r\n<p style="text-align: justify">Are you sure that you want to delete it?</p>'),
('HEURISTIC_DELETION_CONFIRMATION', '<p style="text-align: justify">You are about to delete this heuristic version. Since it has no other version, <strong>this heuristic will be deleted too</strong>. If you continue, <strong>you won''t be able to retrieve them!</strong></p>\r\n<p style="text-align: justify">Are you sure that you want to delete them?</p>'),
('HEURISTIC_PUBLICATION_CONFIRMATION', '<p style="text-align: justify;">By publishing this Contribution on the MASH platform/website, you grant starting from
    <select id="publication_delay">
        <option value="0" selected="yes">today</option>
        <option value="1">$DATE1</option>
        <option value="2">$DATE2</option>
        <option value="3">$DATE3</option>
        <option value="4">$DATE4</option>
    </select>
    the <a target="_blank" href="http://www.idiap.ch">Idiap research institute</a> the right to use, reproduce, compile, distribute, sell or use it in any way subject to the terms of the <a target="_blank" href="http://www.gnu.org/licenses/gpl.html">GNU GPL v2.0</a> license.</p>

<p><input id="publication_accepted" type="checkbox" style="margin-right:4px;">"I warrant I own all intellectual property rights on the Contribution published and that it does not infringe any third party’s right or the MASH Terms and conditions."<p>'),
('HOMEPAGE', '<p>The MASH project is a three-year research initiative involving five European institutions with expertise in machine learning. It aims at developing new learning algorithms based on complex hand-designed prior models. This will be achieved through the study of novel theoretical tools and software to facilitate the collaborative design and the exploitation of large families of <em>heuristics</em> written by extended groups of contributors.</p>\r\n        \r\n<p>The core principle behind this project is that the only venue to design artificial cognitive systems as complex as natural nervous systems, we have to gather a very large group of contributors, providing small dedicated software modules. All this pieces will be combined in a principled manner with techniques for the statistical learning theory.</p>\r\n\r\n<p><strong>Any contributor is of interest to this project. Whatever is your technical background and your programming skills, your personal knowledge and understanding of the world can bring missing capabilities to the system. There is no requirement of having a background in statistical learning, artificial intelligence or mathematics to participate. As long as you can program in C++, please try.</strong></p>\r\n\r\n<p>This project is funded by the <a href="http://cordis.europa.eu/fp7/">7th Framework Program of the European Union.</a></p>');


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
