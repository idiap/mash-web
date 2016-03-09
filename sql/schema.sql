SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";

--
-- Database: `mash`
--

-- --------------------------------------------------------

--
-- Table structure for table `accounts_userprofile`
--

CREATE TABLE IF NOT EXISTS `accounts_userprofile` (
  `id` int(11) NOT NULL auto_increment,
  `user_id` int(11) NOT NULL,
  `forum_user_id` int(11) default NULL,
  `wiki_user_id` int(11) default NULL,
  `project_member` bool NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `forum_user_id_refs_user_id_54def1a8` (`forum_user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=9 ;

-- --------------------------------------------------------

--
-- Table structure for table `django_site`
--

CREATE TABLE IF NOT EXISTS `django_site` (
  `id` int(11) NOT NULL auto_increment,
  `domain` varchar(100) NOT NULL,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=2 ;

-- --------------------------------------------------------

--
-- Table structure for table `menu_menuitem`
--

CREATE TABLE IF NOT EXISTS `menu_menuitem` (
  `id` int(11) NOT NULL auto_increment,
  `label` varchar(200) NOT NULL,
  `link` varchar(200) NOT NULL,
  `index` int(10) unsigned NOT NULL,
  `display` varchar(9) NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=14 ;

-- --------------------------------------------------------

--
-- Table structure for table `registration_registrationprofile`
--

CREATE TABLE IF NOT EXISTS `registration_registrationprofile` (
  `id` int(11) NOT NULL auto_increment,
  `user_id` int(11) NOT NULL,
  `activation_key` varchar(40) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=21 ;

-- --------------------------------------------------------

--
-- Table structure for table `sessionprofile_sessionprofile`
--

CREATE TABLE IF NOT EXISTS `sessionprofile_sessionprofile` (
  `id` int(11) NOT NULL auto_increment,
  `session_id` varchar(40) NOT NULL,
  `user_id` int(11) default NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `session_id` (`session_id`),
  KEY `sessionprofile_sessionprofile_user_id` (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=52 ;

-- --------------------------------------------------------

--
-- Table structure for table `texts_db_text`
--

CREATE TABLE IF NOT EXISTS `texts_db_text` (
  `id` int(11) NOT NULL auto_increment,
  `name` varchar(40) NOT NULL,
  `content` longtext NOT NULL,
  PRIMARY KEY  (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=11 ;
