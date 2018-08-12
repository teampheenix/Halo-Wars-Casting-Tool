"""Define the main window."""
import logging
import os

import markdown2
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QComboBox,
                             QCompleter, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QMainWindow, QMenu, QMessageBox,
                             QPushButton, QSizePolicy, QSlider, QSpacerItem,
                             QTabWidget, QToolButton, QVBoxLayout, QWidget)

import hwctool.settings
import hwctool.settings.config
from hwctool.settings.client_config import ClientConfig
from hwctool.view.subBrowserSources import SubwindowBrowserSources
from hwctool.view.subConnections import SubwindowConnections
from hwctool.view.subMarkdown import SubwindowMarkdown
from hwctool.view.subStyles import SubwindowStyles
from hwctool.view.widgets import LedIndicator, MonitoredLineEdit, ProfileMenu

# create logger
module_logger = logging.getLogger('hwctool.view.main')


class MainWindow(QMainWindow):
    """Show the main window of SCCT."""

    EXIT_CODE_REBOOT = -123

    def __init__(self, controller, app, showChangelog):
        """Init the main window."""
        try:
            super().__init__()

            self._save = True
            self.tlock = TriggerLock()
            self.controller = controller

            with self.tlock:
                self.createFormMatchDataBox()
            self.createTabs()
            self.createHorizontalGroupBox()
            self.createBackgroundTasksBox()

            self.createMenuBar()

            mainLayout = QVBoxLayout()
            mainLayout.addWidget(self.tabs, 0)
            mainLayout.addWidget(self.fromMatchDataBox, 1)
            mainLayout.addWidget(self.backgroundTasksBox, 0)
            mainLayout.addWidget(self.horizontalGroupBox, 0)

            self.setWindowTitle(
                "Halo Wars Casting Tool v{}".format(hwctool.__version__))

            self.window = QWidget()
            self.window.setLayout(mainLayout)
            self.setCentralWidget(self.window)

            # self.size
            self.statusBar()

            self.leds = dict()
            for scope in self.controller.websocketThread.get_primary_scopes():
                self.leds[scope] = LedIndicator(self)

            for key, led in self.leds.items():
                self.controller.toogleLEDs(0, key, self)
                self.statusBar().addPermanentWidget(led)

            self.app = app
            self.controller.setView(self)
            self.controller.refreshButtonStatus()

            self.processEvents()
            self.settings = QSettings(
                ClientConfig.APP_NAME, ClientConfig.COMPANY_NAME)
            self.restoreGeometry(self.settings.value(
                "geometry", self.saveGeometry()))
            self.restoreState(self.settings.value(
                "windowState", self.saveState()))

            self.mysubwindows = dict()

            self.show()
            self.raise_()

            if showChangelog:
                self.openChangelog()

        except Exception as e:
            module_logger.exception("message")

    def showAbout(self):
        """Show subwindow with about info."""
        html = markdown2.markdown_path(
            hwctool.settings.getResFile("about.md"))

        html = html.replace("%VERSION%", hwctool.__version__)
        if(not hwctool.__new_version__):
            new_version = _("Halo Wars Casting Tool is up to date.")
        else:
            new_version = _("The new version {} is available!").format(
                hwctool.__latest_version__)
        html = html.replace('%NEW_VERSION%', new_version)

        # use self as parent here
        QMessageBox.about(
            self, _("Halo Wars Casting Tool - About"), html)

    def closeEvent(self, event):
        """Close and clean up window."""
        try:
            try:
                for name, window in self.mysubwindows.items():
                    if(window and window.isVisible()):
                        window.close()
            finally:
                self.settings.setValue("geometry", self.saveGeometry())
                self.settings.setValue("windowState", self.saveState())
                self.controller.cleanUp(self._save)
                QMainWindow.closeEvent(self, event)
                # event.accept()
        except Exception as e:
            module_logger.exception("message")

    def createMenuBar(self):
        """Create the menu bar."""
        try:
            menubar = self.menuBar()
            settingsMenu = menubar.addMenu(_('Settings'))

            apiAct = QAction(QIcon(hwctool.settings.getResFile(
                'browser.png')), _('Browser Sources'), self)
            apiAct.setToolTip(
                _('Edit Settings for all Browser Sources'))
            apiAct.triggered.connect(self.openBrowserSourcesDialog)
            settingsMenu.addAction(apiAct)
            apiAct = QAction(QIcon(hwctool.settings.getResFile(
                'twitch.png')), _('Twitch && Nightbot'), self)
            apiAct.setToolTip(
                _('Edit Intro-Settings and API-Settings'
                  ' for Twitch and Nightbot'))
            apiAct.triggered.connect(self.openApiDialog)
            settingsMenu.addAction(apiAct)
            styleAct = QAction(QIcon(hwctool.settings.getResFile(
                'pantone.png')), _('Styles'), self)
            styleAct.setToolTip('')
            styleAct.triggered.connect(self.openStyleDialog)
            settingsMenu.addAction(styleAct)

            self.createBrowserSrcMenu()

            ProfileMenu(self, self.controller)

            infoMenu = menubar.addMenu(_('Info && Links'))

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'about.png')), _('About'), self)
            myAct.triggered.connect(self.showAbout)
            infoMenu.addAction(myAct)

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'readme.ico')), _('Readme'), self)
            myAct.triggered.connect(self.openReadme)
            infoMenu.addAction(myAct)

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'update.png')), _('Check for new version'), self)
            myAct.triggered.connect(lambda: self.controller.checkVersion(True))
            infoMenu.addAction(myAct)

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'changelog.png')), _('Changelog'), self)
            myAct.triggered.connect(self.openChangelog)
            infoMenu.addAction(myAct)

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'folder.png')), _('Open log folder'), self)
            myAct.triggered.connect(lambda: os.startfile(
                hwctool.settings.getAbsPath(hwctool.settings.getLogDir())))
            infoMenu.addAction(myAct)

            infoMenu.addSeparator()

            websiteAct = QAction(
                QIcon(
                    hwctool.settings.getResFile('hwct.ico')),
                'Halo Wars Casting Tool', self)
            websiteAct.triggered.connect(lambda: self.controller.openURL(
                "https://teampheenix.github.io/StarCraft-Casting-Tool/"))
            infoMenu.addAction(websiteAct)

            discordAct = QAction(
                QIcon(
                    hwctool.settings.getResFile('discord.png')),
                'Discord', self)
            discordAct.triggered.connect(lambda: self.controller.openURL(
                "https://discord.gg/G9hFEfh"))
            infoMenu.addAction(discordAct)

            ixAct = QAction(QIcon(hwctool.settings.getResFile(
                'icon.png')), 'team pheeniX', self)
            ixAct.triggered.connect(
                lambda: self.controller.openURL("http://team-pheenix.de"))
            infoMenu.addAction(ixAct)

            infoMenu.addSeparator()

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'patreon.png')), _('Become a Patron'), self)
            myAct.triggered.connect(lambda: self.controller.openURL(
                "https://www.patreon.com/StarCraftCastingTool"))
            infoMenu.addAction(myAct)

            myAct = QAction(QIcon(hwctool.settings.getResFile(
                'donate.ico')), _('Donate via PayPal'), self)
            myAct.triggered.connect(lambda: self.controller.openURL(
                "https://paypal.me/StarCraftCastingTool"))
            infoMenu.addAction(myAct)

        except Exception as e:
            module_logger.exception("message")

    def createBrowserSrcMenu(self):
        menubar = self.menuBar()
        main_menu = menubar.addMenu(_('Browser Sources'))

        srcs = []
        srcs.append({'name': _('Intro'),
                     'file': 'intro.html',
                     'settings': lambda: self.openBrowserSourcesDialog(
                     'intro')})
        srcs.append({'name': _('Score'),
                     'file': 'score.html'})

        act = QAction(QIcon(hwctool.settings.getResFile(
            'folder.png')), _('Open Folder'), self)
        act.triggered.connect(lambda: os.startfile(
            hwctool.settings.getAbsPath(hwctool.settings.casting_html_dir)))
        main_menu.addAction(act)
        main_menu.addSeparator()

        for src in srcs:
            myMenu = QMenu(src['name'], self)
            sub = src.get('sub', False)
            if sub:
                for icon in sub:
                    mySubMenu = QMenu(icon['name'], self)
                    icon['file'] = os.path.join(
                        hwctool.settings.casting_html_dir, icon['file'])
                    act = QAction(QIcon(hwctool.settings.getResFile(
                        'html.png')), _('Open in Browser'), self)
                    act.triggered.connect(
                        lambda x,
                        file=icon['file']: self.controller.openURL(
                            hwctool.settings.getAbsPath(file)))
                    mySubMenu.addAction(act)
                    act = QAction(QIcon(hwctool.settings.getResFile(
                        'copy.png')), _('Copy URL to Clipboard'), self)
                    act.triggered.connect(
                        lambda x, file=icon['file']:
                        QApplication.clipboard().setText(
                            hwctool.settings.getAbsPath(file)))
                    mySubMenu.addAction(act)
                    if icon.get('settings', None) is not None:
                        act = QAction(QIcon(hwctool.settings.getResFile(
                            'browser.png')), _('Settings'), self)
                        act.triggered.connect(icon['settings'])
                        mySubMenu.addAction(act)
                    myMenu.addMenu(mySubMenu)
            else:
                src['file'] = os.path.join(
                    hwctool.settings.casting_html_dir, src['file'])
                act = QAction(QIcon(hwctool.settings.getResFile(
                    'html.png')), _('Open in Browser'), self)
                act.triggered.connect(
                    lambda x,
                    file=src['file']: self.controller.openURL(
                        hwctool.settings.getAbsPath(file)))
                myMenu.addAction(act)
                act = QAction(QIcon(hwctool.settings.getResFile(
                    'copy.png')), _('Copy URL to Clipboard'), self)
                act.triggered.connect(
                    lambda x, file=src['file']:
                    QApplication.clipboard().setText(
                        hwctool.settings.getAbsPath(file)))
                myMenu.addAction(act)

            if src.get('settings', None) is not None:
                act = QAction(QIcon(hwctool.settings.getResFile(
                    'browser.png')), _('Settings'), self)
                act.triggered.connect(src['settings'])
                myMenu.addAction(act)
            main_menu.addMenu(myMenu)

        main_menu.addSeparator()

        apiAct = QAction(QIcon(hwctool.settings.getResFile(
            'browser.png')), _('Settings'), self)
        apiAct.setToolTip(
            _('Edit Settings for all Browser Sources'))
        apiAct.triggered.connect(self.openBrowserSourcesDialog)
        main_menu.addAction(apiAct)

        styleAct = QAction(QIcon(hwctool.settings.getResFile(
            'pantone.png')), _('Styles'), self)
        styleAct.setToolTip('')
        styleAct.triggered.connect(self.openStyleDialog)
        main_menu.addAction(styleAct)

    def openApiDialog(self):
        """Open subwindow with connection settings."""
        self.mysubwindows['connections'] = SubwindowConnections()
        self.mysubwindows['connections'].createWindow(self)
        self.mysubwindows['connections'].show()

    def openStyleDialog(self):
        """Open subwindow with style settings."""
        self.mysubwindows['styles'] = SubwindowStyles()
        self.mysubwindows['styles'].createWindow(self)
        self.mysubwindows['styles'].show()

    def openBrowserSourcesDialog(self, tab=''):
        """Open subwindow with browser sources settings."""
        self.mysubwindows['browser'] = SubwindowBrowserSources()
        self.mysubwindows['browser'].createWindow(self, tab)
        self.mysubwindows['browser'].show()

    def openReadme(self):
        """Open subwindow with readme viewer."""
        self.mysubwindows['readme'] = SubwindowMarkdown()
        self.mysubwindows['readme'].createWindow(
            self, _("Readme"),
            hwctool.settings.getResFile('readme.ico'),
            hwctool.settings.getResFile("../README.md"))
        self.mysubwindows['readme'].show()

    def openChangelog(self):
        """Open subwindow with readme viewer."""
        self.mysubwindows['changelog'] = SubwindowMarkdown()
        self.mysubwindows['changelog'].createWindow(
            self, "Halo Wars Casting Tool " + _("Changelog"),
            hwctool.settings.getResFile("changelog.png"),
            hwctool.settings.getResFile("../CHANGELOG.md"))
        self.mysubwindows['changelog'].show()

    def changeLanguage(self, language):
        """Change the language."""
        hwctool.settings.config.parser.set("SCT", "language", language)
        self.restart()

    def createTabs(self):
        """Create tabs in main window."""
        try:
            # Initialize tab screen
            self.tabs = QTabWidget()
            self.tab2 = QWidget()
            # self.tabs.resize(300,200)

            # Add tabs
            self.tabs.addTab(self.tab2, _("Custom Match"))

            # Create second tab

            self.tab2.layout = QVBoxLayout()

            container = QHBoxLayout()

            label = QLabel()
            label.setMinimumWidth(self.labelWidth)
            container.addWidget(label, 0)

            label = QLabel(_("Match Format:"))
            label.setMinimumWidth(80)
            container.addWidget(label, 0)

            container.addWidget(QLabel(_("Best of")), 0)

            self.cb_bestof = QComboBox()
            for idx in range(0, hwctool.settings.max_no_sets):
                self.cb_bestof.addItem(str(idx + 1))
            self.cb_bestof.setCurrentIndex(3)
            string = _('"Best of 6/4": First, a Bo5/3 is played and the'
                       ' ace map gets extended to a Bo3 if needed;'
                       ' Best of 2: Bo3 with only two maps played.')
            self.cb_bestof.setToolTip(string)
            self.cb_bestof.setMaximumWidth(40)
            self.cb_bestof.currentIndexChanged.connect(self.changeBestOf)
            container.addWidget(self.cb_bestof, 0)

            container.addWidget(QLabel(_(" but at least")), 0)

            self.cb_minSets = QComboBox()

            self.cb_minSets.setToolTip(
                _('Minimum number of maps played (even if the match'
                  ' is decided already)'))
            self.cb_minSets.setMaximumWidth(40)
            container.addWidget(self.cb_minSets, 0)
            container.addWidget(
                QLabel(" " + _("maps") + "  "), 0)
            self.cb_minSets.currentIndexChanged.connect(
                lambda idx: self.highlightApplyCustom())

            label = QLabel("")
            container.addWidget(label, 1)

            self.applycustom_is_highlighted = False

            self.pb_applycustom = QToolButton()
            action = QAction(_("Apply Format"))
            action.triggered.connect(self.applycustom_click)
            self.pb_applycustom.setDefaultAction(action)

            self.pb_applycustom.setFixedWidth(150)
            container.addWidget(self.pb_applycustom, 0)

            self.defaultButtonPalette = self.pb_applycustom.palette()

            self.tab2.layout.addLayout(container)

            container = QHBoxLayout()

            label = QLabel()
            label.setMinimumWidth(self.labelWidth)
            container.addWidget(label, 0)

            label = QLabel(_("Match-URL:"))
            label.setMinimumWidth(80)
            container.addWidget(label, 0)

            self.le_url_custom = MonitoredLineEdit()
            self.le_url_custom.setAlignment(Qt.AlignCenter)
            self.le_url_custom.setToolTip(
                _('Optionally specify the Match-URL,'
                  ' e.g., for Nightbot commands'))
            self.le_url_custom.setPlaceholderText(
                _("Specify the Match-URL of your Custom Match"))

            completer = QCompleter(
                ["http://"], self.le_url_custom)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setCompletionMode(
                QCompleter.UnfilteredPopupCompletion)
            completer.setWrapAround(True)
            self.le_url_custom.setCompleter(completer)
            self.le_url_custom.setMinimumWidth(360)
            self.le_url_custom.textModified.connect(self.highlightApplyCustom)

            container.addWidget(self.le_url_custom, 11)

            label = QLabel("")
            container.addWidget(label, 1)

            self.pb_resetdata = QPushButton(
                _("Reset Match Data"))
            self.pb_resetdata.setFixedWidth(150)
            self.pb_resetdata.clicked.connect(self.resetdata_click)
            container.addWidget(self.pb_resetdata, 0)

            self.tab2.layout.addLayout(container)

            self.tab2.setLayout(self.tab2.layout)

        except Exception as e:
            module_logger.exception("message")

    def changeBestOf(self, bestof):
        """Change the minimum sets combo box on change of BoX."""
        bestof = bestof + 1
        self.cb_minSets.clear()
        self.highlightApplyCustom()
        for idx in range(0, bestof):
            self.cb_minSets.addItem(str(idx + 1))
            if bestof == 2:
                self.cb_minSets.setCurrentIndex(1)
            else:
                self.cb_minSets.setCurrentIndex((bestof - 1) / 2)

    def updatePlayerCompleters(self):
        """Refresh the completer for the player line edits."""
        list = ["TBD"] + self.controller.historyManager.getPlayerList()
        for player_idx in range(self.max_no_sets):
            for team_idx in range(2):
                completer = QCompleter(
                    list, self.le_player[team_idx][player_idx])
                completer.setCaseSensitivity(
                    Qt.CaseInsensitive)
                completer.setCompletionMode(
                    QCompleter.InlineCompletion)
                completer.setWrapAround(True)
                self.le_player[team_idx][player_idx].setCompleter(
                    completer)

    def createFormMatchDataBox(self):
        """Create the froms for the match data."""
        try:

            self.max_no_sets = hwctool.settings.max_no_sets
            self.scoreWidth = 35
            self.raceWidth = 100
            self.labelWidth = 25
            self.mimumLineEditWidth = 130

            self.fromMatchDataBox = QGroupBox(_("Match Data"))
            layout2 = QVBoxLayout()

            self.le_league = MonitoredLineEdit()
            self.le_league.setText("League TBD")
            self.le_league.setAlignment(Qt.AlignCenter)
            self.le_league.setPlaceholderText("League TBD")
            self.le_league.textModified.connect(self.league_changed)
            policy = QSizePolicy()
            policy.setHorizontalStretch(3)
            policy.setHorizontalPolicy(QSizePolicy.Expanding)
            policy.setVerticalStretch(1)
            policy.setVerticalPolicy(QSizePolicy.Fixed)
            self.le_league.setSizePolicy(policy)
            self.le_player = [[MonitoredLineEdit() for x in range(
                self.max_no_sets)] for y in range(2)]
            self.cb_race = [[QComboBox() for x in range(self.max_no_sets)]
                            for y in range(2)]
            self.sl_score = [QSlider(Qt.Horizontal)
                             for y in range(self.max_no_sets)]
            self.label_set = [QLabel('#{}'.format(y + 1), self)
                              for y in range(self.max_no_sets)]
            self.setContainer = [QHBoxLayout()
                                 for y in range(self.max_no_sets)]

            container = QGridLayout()

            button = QPushButton()
            pixmap = QIcon(
                hwctool.settings.getResFile('update.png'))
            button.setIcon(pixmap)
            button.clicked.connect(
                lambda: self.controller.swapTeams())
            button.setFixedWidth(self.labelWidth)
            button.setToolTip(_("Swap players."))
            container.addWidget(button, 0, 0, 1, 1)

            label = QLabel(_("League:"))
            label.setAlignment(Qt.AlignCenter)
            label.setFixedWidth(self.raceWidth)
            container.addWidget(label, 0, 1, 1, 1)

            container.addWidget(self.le_league, 0, 2, 1, 3)

            label = QLabel("")
            label.setFixedWidth(self.raceWidth)
            container.addWidget(label, 0, 5, 1, 1)

            layout2.addLayout(container)

            for player_idx in range(self.max_no_sets):
                for team_idx in range(2):
                    self.cb_race[team_idx][player_idx].\
                        currentIndexChanged.connect(
                        lambda idx,
                        t=team_idx,
                        p=player_idx: self.race_changed(t, p))
                    self.le_player[team_idx][player_idx].textModified.connect(
                        lambda t=team_idx,
                        p=player_idx: self.player_changed(t, p))
                    self.le_player[team_idx][player_idx].setText("TBD")
                    self.le_player[team_idx][player_idx].setAlignment(
                        Qt.AlignCenter)
                    self.le_player[team_idx][player_idx].setPlaceholderText(
                        _("Player {} of team {}").format(player_idx + 1,
                                                         team_idx + 1))
                    self.le_player[team_idx][player_idx].setMinimumWidth(
                        self.mimumLineEditWidth)

                    for race in hwctool.settings.races:
                        self.cb_race[team_idx][player_idx].addItem(race)

                    self.cb_race[team_idx][player_idx].setFixedWidth(
                        self.raceWidth)

                self.sl_score[player_idx].setMinimum(-1)
                self.sl_score[player_idx].setMaximum(1)
                self.sl_score[player_idx].setValue(0)
                self.sl_score[player_idx].setTickPosition(
                    QSlider.TicksBothSides)
                self.sl_score[player_idx].setTickInterval(1)
                self.sl_score[player_idx].setTracking(False)
                self.sl_score[player_idx].valueChanged.connect(
                    lambda x,
                    player_idx=player_idx: self.sl_changed(player_idx, x))
                self.sl_score[player_idx].setToolTip(_('Set the score'))
                self.sl_score[player_idx].setFixedWidth(self.scoreWidth)

                self.setContainer[player_idx] = QHBoxLayout()
                # self.label_set[player_idx].setText("#" + str(player_idx + 1))
                self.label_set[player_idx].setAlignment(Qt.AlignCenter)
                self.label_set[player_idx].setFixedWidth(self.labelWidth)
                self.setContainer[player_idx].addWidget(
                    self.label_set[player_idx], 0)
                self.setContainer[player_idx].addWidget(
                    self.cb_race[0][player_idx], 0)
                self.setContainer[player_idx].addWidget(
                    self.le_player[0][player_idx], 4)
                self.setContainer[player_idx].addWidget(
                    self.sl_score[player_idx], 0)
                self.setContainer[player_idx].addWidget(
                    self.le_player[1][player_idx], 4)
                self.setContainer[player_idx].addWidget(
                    self.cb_race[1][player_idx], 0)
                layout2.addLayout(self.setContainer[player_idx])

            layout2.addItem(QSpacerItem(
                0, 0, QSizePolicy.Minimum,
                QSizePolicy.Expanding))
            self.fromMatchDataBox.setLayout(layout2)

            self.updatePlayerCompleters()

        except Exception as e:
            module_logger.exception("message")

    def createHorizontalGroupBox(self):
        """Create horizontal group box for tasks."""
        try:
            self.horizontalGroupBox = QGroupBox(_("Tasks"))
            layout = QHBoxLayout()

            self.pb_twitchupdate = QPushButton(
                _("Update Twitch Title"))
            self.pb_twitchupdate.clicked.connect(self.updatetwitch_click)

            self.pb_nightbotupdate = QPushButton(
                _("Update Nightbot"))
            self.pb_nightbotupdate.clicked.connect(self.updatenightbot_click)

            self.pb_resetscore = QPushButton(_("Reset Score"))
            self.pb_resetscore.clicked.connect(self.resetscore_click)

            layout.addWidget(self.pb_twitchupdate)
            layout.addWidget(self.pb_nightbotupdate)
            layout.addWidget(self.pb_resetscore)

            self.horizontalGroupBox.setLayout(layout)

        except Exception as e:
            module_logger.exception("message")

    def createBackgroundTasksBox(self):
        """Create group box for background tasks."""
        try:
            self.backgroundTasksBox = QGroupBox(
                _("Background Tasks"))

            self.cb_autoTwitch = QCheckBox(
                _("Auto Twitch Update"))
            self.cb_autoTwitch.setChecked(False)
            self.cb_autoTwitch.stateChanged.connect(self.autoTwitch_change)

            self.cb_autoNightbot = QCheckBox(
                _("Auto Nightbot Update"))
            self.cb_autoNightbot.setChecked(False)
            self.cb_autoNightbot.stateChanged.connect(
                self.autoNightbot_change)

            layout = QGridLayout()

            layout.addWidget(self.cb_autoTwitch, 0, 0)
            layout.addWidget(self.cb_autoNightbot, 0, 1)

            self.backgroundTasksBox.setLayout(layout)

        except Exception as e:
            module_logger.exception("message")

    def autoTwitch_change(self):
        """Handle change of auto twitch check box."""
        try:
            if(self.cb_autoTwitch.isChecked()):
                self.controller.autoRequestsThread.activateTask('twitch')
            else:
                self.controller.autoRequestsThread.deactivateTask('twitch')
        except Exception as e:
            module_logger.exception("message")

    def autoNightbot_change(self):
        """Handle change of auto twitch check box."""
        try:
            if(self.cb_autoNightbot.isChecked()):
                self.controller.autoRequestsThread.activateTask('nightbot')
            else:
                self.controller.autoRequestsThread.deactivateTask('nightbot')
        except Exception as e:
            module_logger.exception("message")

    def autoUpdate_change(self):
        """Handle change of auto score update check box."""
        try:
            if(self.cb_autoUpdate.isChecked()):
                self.controller.runSC2ApiThread("updateScore")
            else:
                self.controller.stopSC2ApiThread("updateScore")
        except Exception as e:
            module_logger.exception("message")

    def autoToggleScore_change(self):
        """Handle change of toggle score check box."""
        try:
            if(self.cb_autoToggleScore.isChecked()):
                self.controller.runSC2ApiThread("toggleScore")
            else:
                self.controller.stopSC2ApiThread("toggleScore")
        except Exception as e:
            module_logger.exception("message")

    def autoToggleProduction_change(self):
        """Handle change of toggle production tab check box."""
        try:
            if(self.cb_autoToggleProduction.isChecked()):
                self.controller.runSC2ApiThread("toggleProduction")
            else:
                self.controller.stopSC2ApiThread("toggleProduction")
        except Exception as e:
            module_logger.exception("message")

    def applyCustomFormat(self, format):
        """Handle click to apply custom format."""
        QApplication.setOverrideCursor(
            Qt.WaitCursor)
        try:
            with self.tlock:
                self.controller.matchData.applyCustomFormat(format)
                self.controller.updateForms()
                self.resizeWindow()
            self.highlightApplyCustom(False)
        except Exception as e:
            module_logger.exception("message")
        finally:
            QApplication.restoreOverrideCursor()

    def applycustom_click(self):
        """Handle click to apply custom match."""
        QApplication.setOverrideCursor(
            Qt.WaitCursor)
        try:
            with self.tlock:
                self.statusBar().showMessage(_('Applying Custom Match...'))
                msg = self.controller.applyCustom(
                    int(self.cb_bestof.currentText()),
                    False,
                    True,
                    int(self.cb_minSets.currentText()),
                    self.le_url_custom.text().strip())
                self.statusBar().showMessage(msg)
            self.highlightApplyCustom(False)
        except Exception as e:
            module_logger.exception("message")
        finally:
            QApplication.restoreOverrideCursor()

    def resetdata_click(self):
        """Handle click to reset the data."""
        QApplication.setOverrideCursor(
            Qt.WaitCursor)
        try:
            with self.tlock:
                msg = self.controller.resetData()
                self.statusBar().showMessage(msg)
        except Exception as e:
            module_logger.exception("message")
        finally:
            QApplication.restoreOverrideCursor()

    def openBrowser_click(self):
        """Handle request to open URL in browser."""
        try:
            url = self.le_url.text()
            self.controller.openURL(url)
        except Exception as e:
            module_logger.exception("message")

    def updatenightbot_click(self):
        """Handle click to change nightbot command."""
        try:
            self.statusBar().showMessage(_('Updating Nightbot Command...'))
            msg = self.controller.updateNightbotCommand()
            self.statusBar().showMessage(msg)
        except Exception as e:
            module_logger.exception("message")

    def updatetwitch_click(self):
        """Handle click to change twitch title."""
        try:
            self.statusBar().showMessage(_('Updating Twitch Title...'))
            msg = self.controller.updateTwitchTitle()
            self.statusBar().showMessage(msg)
        except Exception as e:
            module_logger.exception("message")

    def resetscore_click(self, myteam=False):
        """Handle click to reset the score."""
        try:
            self.statusBar().showMessage(_('Resetting Score...'))
            with self.tlock:
                for set_idx in range(self.max_no_sets):
                    self.sl_score[set_idx].setValue(0)
                    self.controller.matchData.setMapScore(
                        set_idx, 0, overwrite=True)
                if myteam:
                    self.sl_team.setValue(0)
                    self.controller.matchData.setMyTeam(0)
                if not self.controller.resetWarning():
                    self.statusBar().showMessage('')

        except Exception as e:
            module_logger.exception("message")

    def setScore(self, idx, score, allkill=True):
        """Handle change of the score."""
        try:
            if(self.sl_score[idx].value() == 0):
                self.statusBar().showMessage(_('Updating Score...'))
                with self.tlock:
                    self.sl_score[idx].setValue(score)
                    self.controller.matchData.setMapScore(idx, score, True)
                    if not self.controller.resetWarning():
                        self.statusBar().showMessage('')
                return True
            else:
                return False
        except Exception as e:
            module_logger.exception("message")

    def league_changed(self):
        if not self.tlock.trigger():
            return
        self.controller.matchData.setLeague(self.le_league.text())

    def sl_changed(self, set_idx, value):
        """Handle a new score value."""
        try:
            if self.tlock.trigger():
                if set_idx == -1:
                    self.controller.matchData.setMyTeam(value)
                else:
                    self.controller.matchData.setMapScore(set_idx, value, True)
        except Exception as e:
            module_logger.exception("message")

    def player_changed(self, team_idx, player_idx):
        """Handle a change of player names."""
        if not self.tlock.trigger():
            return
        try:
            player = self.le_player[team_idx][player_idx].text().strip()
            race = self.cb_race[team_idx][player_idx].currentText()
            if(player_idx == 0 and self.controller.matchData.getSolo()):
                for p_idx in range(1, self.max_no_sets):
                    self.le_player[team_idx][p_idx].setText(player)
                    self.player_changed(team_idx, p_idx)
            self.controller.historyManager.insertPlayer(player, race)
            self.controller.matchData.setPlayer(
                team_idx, player_idx,
                self.le_player[team_idx][player_idx].text())

            if race == "Random":
                new_race = self.controller.historyManager.getRace(player)
                if new_race != "Random":
                    index = self.cb_race[team_idx][player_idx].findText(
                        new_race, Qt.MatchFixedString)
                    if index >= 0:
                        self.cb_race[team_idx][player_idx].setCurrentIndex(
                            index)
            elif player.lower() == "tbd":
                self.cb_race[team_idx][player_idx].setCurrentIndex(0)
            self.updatePlayerCompleters()
        except Exception as e:
            module_logger.exception("message")

    def race_changed(self, team_idx, player_idx):
        """Handle a change of player names."""
        if not self.tlock.trigger():
            return
        player = self.le_player[team_idx][player_idx].text().strip()
        race = self.cb_race[team_idx][player_idx].currentText()
        self.controller.historyManager.insertPlayer(player, race)
        self.controller.matchData.setRace(
            team_idx, player_idx,
            self.cb_race[team_idx][player_idx].currentText())
        try:
            if(player_idx == 0 and self.controller.matchData.getSolo()):
                race = self.cb_race[team_idx][0].currentText()
                for player_idx in range(1, self.max_no_sets):
                    index = self.cb_race[team_idx][player_idx].findText(
                        race, Qt.MatchFixedString)
                    if index >= 0:
                        self.cb_race[team_idx][player_idx].setCurrentIndex(
                            index)

        except Exception as e:
            module_logger.exception("message")

    def highlightApplyCustom(self, highlight=True, force=False):
        if not force and not self.tlock.trigger():
            return
        try:
            if self.applycustom_is_highlighted == highlight:
                return highlight
        except AttributeError:
            return False

        if highlight:
            myPalette = self.pb_applycustom.palette()
            myPalette.setColor(QPalette.Background,
                               Qt.darkRed)
            myPalette.setColor(QPalette.ButtonText,
                               Qt.darkRed)
            self.pb_applycustom.setPalette(myPalette)
        else:
            self.pb_applycustom.setPalette(self.defaultButtonPalette)

        self.applycustom_is_highlighted = highlight
        return highlight

    def resizeWindow(self):
        """Resize the window height to size hint."""
        if(not self.isMaximized()):
            self.processEvents()
            self.resize(self.width(), self.sizeHint().height())

    def processEvents(self):
        """Process ten PyQt5 events."""
        for i in range(0, 10):
            self.app.processEvents()

    def restart(self, save=True):
        """Restart the main window."""
        self._save = save
        self.close()
        self.app.exit(self.EXIT_CODE_REBOOT)


class TriggerLock():
    def __init__(self):
        self.__trigger = True

    def __enter__(self):
        self.__trigger = False

    def __exit__(self, type, value, traceback):
        self.__trigger = True

    def trigger(self):
        return bool(self.__trigger)
