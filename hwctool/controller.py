"""Control all other modules."""
import logging
import os
import shutil
import sys
import webbrowser

import gtts
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QMessageBox

import hwctool.settings
import hwctool.tasks.nightbot
import hwctool.tasks.twitch
from hwctool.matchdata import matchData
from hwctool.settings.history import HistoryManager
from hwctool.settings.placeholders import PlaceholderList
from hwctool.tasks.auth import AuthThread
from hwctool.tasks.autorequests import AutoRequestsThread
from hwctool.tasks.textfiles import TextFilesThread
from hwctool.tasks.updater import VersionHandler
from hwctool.tasks.websocket import WebsocketThread
from hwctool.view.widgets import ToolUpdater

# create logger
module_logger = logging.getLogger('hwctool.controller')


class MainController:
    """Control all other modules."""

    def __init__(self):
        """Init controller and connect them with other modules."""
        try:
            self.matchData = matchData(self)
            self.authThread = AuthThread()
            self.authThread.tokenRecived.connect(self.tokenRecived)
            self.textFilesThread = TextFilesThread(self.matchData)
            self.matchData.dataChanged.connect(self.handleMatchDataChange)
            self.matchData.metaChangedSignal.connect(self.matchMetaDataChanged)
            self.versionHandler = VersionHandler(self)
            self.websocketThread = WebsocketThread(self)
            self.websocketThread.socketConnectionChanged.connect(
                self.toogleLEDs)
            self.websocketThread.introShown.connect(self.updatePlayerIntroIdx)
            self.runWebsocketThread()
            self.autoRequestsThread = AutoRequestsThread(self)
            self.placeholders = self.placeholderSetup()
            self._warning = False
            self.checkVersion()
            self.historyManager = HistoryManager()
            self.initPlayerIntroData()

        except Exception as e:
            module_logger.exception("message")
            raise

    def checkVersion(self, force=False):
        """Check for new version."""
        try:
            self.versionHandler.disconnect()
        except Exception:
            pass
        try:
            self.noNewVersion.disconnect()
        except Exception:
            pass

        self.versionHandler.newVersion.connect(
            lambda x: self.newVersion(x, force))
        if force:
            self.versionHandler.noNewVersion.connect(
                lambda: self.displayWarning(_("This version is up to date.")))

        self.versionHandler.activateTask('version_check')

    def placeholderSetup(self):
        """Define and connect placeholders."""
        placeholders = PlaceholderList()

        placeholders.addConnection("Team1", lambda:
                                   self.matchData.getTeamOrPlayer(0))
        placeholders.addConnection("Team2", lambda:
                                   self.matchData.getTeamOrPlayer(1))
        placeholders.addConnection("URL", self.matchData.getURL)
        placeholders.addConnection(
            "BestOf", lambda: str(self.matchData.getBestOfRaw()))
        placeholders.addConnection("League", self.matchData.getLeague)
        placeholders.addConnection("Score", self.matchData.getScoreString)

        return placeholders

    def setView(self, view):
        """Connect view."""
        self.view = view
        try:
            self.matchData.readJsonFile()
            with self.view.tlock:
                self.updateForms()
            self.setCBs()
            self.view.resizeWindow()
        except Exception as e:
            module_logger.exception("message")

    def updateForms(self):
        """Update data in forms."""
        try:

            index = self.view.cb_bestof.findText(
                str(self.matchData.getBestOfRaw()),
                Qt.MatchFixedString)
            if index >= 0:
                self.view.cb_bestof.setCurrentIndex(index)

            index = self.view.cb_minSets.findText(
                str(self.matchData.getMinSets()),
                Qt.MatchFixedString)
            if index >= 0:
                self.view.cb_minSets.setCurrentIndex(index)

            self.view.le_url_custom.setText(self.matchData.getURL())
            self.view.le_league.setText(self.matchData.getLeague())

            for j in range(2):
                for i in range(1, self.matchData.getNoSets()):
                    self.view.le_player[j][i].setReadOnly(
                        self.matchData.getSolo())

            for i in range(min(self.view.max_no_sets,
                               self.matchData.getNoSets())):
                for j in range(2):
                    player = self.matchData.getPlayer(j, i)
                    race = self.matchData.getRace(j, i)
                    self.view.le_player[j][i].setText(player)
                    index = self.view.cb_race[j][i].findText(
                        race, Qt.MatchFixedString)
                    if index >= 0:
                        self.view.cb_race[j][i].setCurrentIndex(index)
                    self.historyManager.insertPlayer(player, race)

                self.view.sl_score[i].setValue(self.matchData.getMapScore(i))

            for i in range(self.matchData.getNoSets(), self.view.max_no_sets):
                for j in range(2):
                    self.view.le_player[j][i].hide()
                    self.view.cb_race[j][i].hide()
                self.view.sl_score[i].hide()
                self.view.label_set[i].hide()

            for i in range(min(self.view.max_no_sets,
                               self.matchData.getNoSets())):
                for j in range(2):
                    self.view.le_player[j][i].show()
                    self.view.cb_race[j][i].show()
                self.view.sl_score[i].show()
                self.view.label_set[i].show()

            self.view.updatePlayerCompleters()
            self.updatePlayerIntros()

        except Exception as e:
            module_logger.exception("message")
            raise

    def applyCustom(self, bestof, allkill, solo, minSets, url):
        """Apply a custom match format."""
        msg = ''
        try:
            with self.matchData.emitLock(True,
                                         self.matchData.metaChangedSignal):
                self.matchData.setCustom(bestof, allkill, solo)
                self.matchData.setMinSets(minSets)
                self.matchData.setURL(url)
                self.matchData.writeJsonFile()
                self.updateForms()
                self.view.resizeWindow()

        except Exception as e:
            msg = str(e)
            module_logger.exception("message")

        return msg

    def resetData(self):
        """Reset data."""
        msg = ''
        try:
            self.matchData.resetData(False)
            self.matchData.writeJsonFile()
            self.updateForms()

        except Exception as e:
            msg = str(e)
            module_logger.exception("message")

        return msg

    def setCBs(self):
        """Update value of check boxes from config."""
        try:
            self.view.cb_autoTwitch.setChecked(
                hwctool.settings.config.parser.getboolean("Form",
                                                          "autotwitch"))
            self.view.cb_autoNightbot.setChecked(
                hwctool.settings.config.parser.getboolean("Form",
                                                          "autonightbot"))

        except Exception as e:
            module_logger.exception("message")

    def uncheckCB(self, cb):
        """Uncheck check boxes on error."""
        if(cb == 'twitch'):
            self.view.cb_autoTwitch.setChecked(False)
        elif(cb == 'nightbot'):
            self.view.cb_autoNightbot.setChecked(False)

    def tokenRecived(self, scope, token):
        """Call to return of token."""
        try:
            subwindow = self.view.mysubwindows['connections']
            getattr(subwindow, '{}Token'.format(scope)).setTextMonitored(token)

            self.view.raise_()
            self.view.show()
            self.view.activateWindow()

            subwindow.raise_()
            subwindow.show()
            subwindow.activateWindow()

        except Exception as e:
            module_logger.exception("message")

    def updateNightbotCommand(self):
        """Update nightbot commands."""
        self.autoRequestsThread.activateTask('nightbot_once')

    def updateTwitchTitle(self):
        """Update twitch title."""
        self.autoRequestsThread.activateTask('twitch_once')

    def openURL(self, url):
        """Open URL in Browser."""
        if(len(url) < 5):
            url = "https://teampheenix.github.io/StarCraft-Casting-Tool/"
        try:
            webbrowser.open(url)
        except Exception as e:
            module_logger.exception("message")

    def runWebsocketThread(self):
        """Run websocket thread."""
        if(not self.websocketThread.isRunning()):
            self.websocketThread.start()
        else:
            module_logger.exception("Thread is still running")

    def stopWebsocketThread(self):
        """Stop websocket thread."""
        try:
            self.websocketThread.stop()
        except Exception as e:
            module_logger.exception("message")

    def cleanUp(self, save=True):
        """Clean up all threads and save config to close program."""
        try:
            module_logger.info("cleanUp called")
            self.authThread.terminate()
            self.stopWebsocketThread()
            self.textFilesThread.terminate()
            self.autoRequestsThread.terminate()
            if save:
                self.saveAll()
        except Exception as e:
            module_logger.exception("message")

    def saveAll(self):
        self.saveConfig()
        self.matchData.writeJsonFile()
        hwctool.settings.saveNightbotCommands()
        self.historyManager.dumpJson()

    def saveConfig(self):
        """Save the settings to the config file."""
        try:
            hwctool.settings.config.parser.set("Form", "autotwitch", str(
                self.view.cb_autoTwitch.isChecked()))
            hwctool.settings.config.parser.set("Form", "autonightbot", str(
                self.view.cb_autoNightbot.isChecked()))

            configFile = open(hwctool.settings.configFile(),
                              'w', encoding='utf-8-sig')
            hwctool.settings.config.parser.write(configFile)
            configFile.close()
        except Exception as e:
            module_logger.exception("message")

    def setRace(self, team_idx, set_idx, race):
        if self.matchData.setRace(team_idx, set_idx, race):
            if race != self.view.cb_race[team_idx][set_idx].currenText():
                with self.view.tlock:
                    index = self.view.cb_race[team_idx][set_idx](
                        race, Qt.MatchFixedString)
                    if index >= 0:
                        self.view.cb_race[team_idx][set_idx](index)

    def toggleWidget(self, widget, condition, ttFalse='', ttTrue=''):
        """Disable or an enable a widget based on a condition."""
        widget.setAttribute(Qt.WA_AlwaysShowToolTips)
        if condition:
            tooltip = ttTrue
        else:
            tooltip = ttFalse
        widget.setToolTip(tooltip)
        widget.setEnabled(condition)

    def refreshButtonStatus(self):
        """Enable or disable buttons depending on config."""
        self.toggleWidget(
            self.view.pb_twitchupdate,
            hwctool.settings.config.twitchIsValid(),
            _('Specify your Twitch Settings to use this feature'),
            '')

        txt = _('Automatically update the title of your' +
                ' twitch channel in the background.')
        self.toggleWidget(
            self.view.cb_autoTwitch,
            hwctool.settings.config.twitchIsValid(),
            _('Specify your Twitch Settings to use this feature'),
            txt)

        self.toggleWidget(
            self.view.cb_autoNightbot,
            hwctool.settings.config.nightbotIsValid(),
            _('Specify your Nightbot Settings to use this feature'),
            _('Automatically update the commands of your' +
              ' nightbot in the background.'))

        self.toggleWidget(
            self.view.pb_nightbotupdate,
            hwctool.settings.config.nightbotIsValid(),
            _('Specify your Nightbot Settings to use this feature'),
            '')

    def linkFile(self, file):
        """Return correct img file ending."""
        for ext in [".jpg", ".png"]:
            if(os.path.isfile(hwctool.settings.getAbsPath(file + ext))):
                return file + ext
        return ""

    def updateHotkeys(self):
        """Refresh hotkeys."""
        if(self.websocketThread.isRunning()):
            self.websocketThread.unregister_hotkeys(force=True)
            self.websocketThread.register_hotkeys()

    def updatePlayerIntroIdx(self):
        self.__playerIntroIdx = (self.__playerIntroIdx + 1) % 2

    def initPlayerIntroData(self):
        """Initalize player intro data."""
        self.__playerIntroData = dict()
        self.__playerIntroIdx = 0
        for player_idx in range(2):
            data = dict()
            data['name'] = "pressure"
            data['race'] = "Random"
            data['logo'] = 'src/img/races/Random.png'
            data['team'] = "Random"
            data['display'] = "block"
            self.__playerIntroData[player_idx] = data

    def getPlayerIntroData(self, idx):
        """Return player intro."""
        if idx == -1:
            idx = self.__playerIntroIdx
        data = self.__playerIntroData[idx]
        data['volume'] = hwctool.settings.config.parser.getint(
            "Intros", "sound_volume")
        data['tts_volume'] = hwctool.settings.config.parser.getint(
            "Intros", "tts_volume")
        data['display_time'] = hwctool.settings.config.parser.getfloat(
            "Intros", "display_time")
        data['animation'] = hwctool.settings.config.parser.get(
            "Intros", "animation") .strip().lower()
        if hwctool.settings.config.parser.getboolean(
                "Style", "use_custom_font"):
            data['font'] = hwctool.settings.config.parser.get(
                "Style", "custom_font")
        return data

    def updatePlayerIntros(self):
        """Update player intro files."""
        module_logger.info("updatePlayerIntros")

        tts_active = hwctool.settings.config.parser.getboolean(
            "Intros", "tts_active")
        tts_lang = hwctool.settings.config.parser.get(
            "Intros", "tts_lang")
        tts_scope = hwctool.settings.config.parser.get(
            "Intros", "tts_scope")

        set_idx = name = self.matchData.getNextSet(True)

        for player_idx in range(2):
            name = self.matchData.getPlayer(player_idx, set_idx)
            race = self.matchData.getRace(player_idx, set_idx)
            self.__playerIntroData[player_idx]['name'] = name
            self.__playerIntroData[player_idx]['team'] = race
            self.__playerIntroData[player_idx]['race'] = race
            file = 'src/img/races/{}.png'
            self.__playerIntroData[player_idx]['logo'] = \
                file.format(race.replace(' ', '_'))
            self.__playerIntroData[player_idx]['display'] = "block"
            self.__playerIntroIdx = 0

            try:
                if tts_active:
                    if tts_scope == 'team_player':
                        text = "{} as {}".format(name, race)
                    else:
                        text = name
                    tts = gtts.gTTS(text=text, lang=tts_lang)
                    tts_file = 'src/sound/player{}.mp3'.format(player_idx + 1)
                    file = os.path.normpath(os.path.join(
                        hwctool.settings.getAbsPath(
                            hwctool.settings.casting_html_dir),
                        tts_file))
                    tts.save(file)
                else:
                    tts_file = None
                self.__playerIntroData[player_idx]['tts'] = tts_file

            except Exception as e:
                self.__playerIntroData[player_idx]['tts'] = None
                module_logger.exception("message")

    def getMapImg(self, map, fullpath=False):
        """Get map image from map name."""
        if map == 'TBD':
            return map
        mapdir = hwctool.settings.getAbsPath(
            hwctool.settings.casting_html_dir)
        mapimg = os.path.normpath(os.path.join(
            mapdir, "src/img/maps", map.replace(" ", "_")))
        mapimg = os.path.basename(self.linkFile(mapimg))
        if not mapimg:
            mapimg = "TBD"
            self.displayWarning(_("Warning: Map '{}' not found!").format(map))

        if(fullpath):
            return os.path.normpath(os.path.join(
                mapdir, "src/img/maps", mapimg))
        else:
            return mapimg

    def addMap(self, file, mapname):
        """Add a new map via file and name."""
        _, ext = os.path.splitext(file)
        mapdir = hwctool.settings.getAbsPath(
            hwctool.settings.casting_html_dir)
        map = mapname.strip().replace(" ", "_") + ext.lower()
        newfile = os.path.normpath(os.path.join(mapdir, "src/img/maps", map))
        shutil.copy(file, newfile)
        if mapname not in hwctool.settings.maps:
            hwctool.settings.maps.append(mapname)

    def deleteMap(self, map):
        """Delete map and file."""
        os.remove(self.getMapImg(map, True))
        hwctool.settings.maps.remove(map)

    def swapTeams(self):
        with self.view.tlock:
            self.matchData.swapTeams()
            self.updateForms()

    def displayWarning(self, msg="Warning: Something went wrong..."):
        """Display a warning in status bar."""
        msg = _(msg)
        self._warning = True
        self.view.statusBar().showMessage(msg)

    def resetWarning(self):
        """Display or reset warning now."""
        warning = self._warning
        self._warning = False
        return warning

    def toogleLEDs(self, num, path, view=None):
        """Indicate when browser sources are connected."""
        if not view:
            view = self.view
        view.leds[path].setChecked(num > 0)
        name = path.replace('_', ' ').title()
        view.leds[path].setToolTip(
            _("{} {} Browser Source(s) connected.").format(num, name))

    def matchMetaDataChanged(self):
        data = self.matchData.getScoreData()
        self.websocketThread.sendData2Path("score", "ALL_DATA", data)
        self.updatePlayerIntros()

    def handleMatchDataChange(self, label, object):
        if label == 'team':
            if not self.matchData.getSolo():
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_TEXT',
                    {'id': 'team{}'.format(object['idx'] + 1),
                     'text': object['value']})
        elif label == 'score':
            score = self.matchData.getScore()
            for idx in range(2):
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_TEXT', {
                        'id': 'score{}'.format(idx + 1),
                        'text': str(score[idx])})
                color = self.matchData.getScoreIconColor(
                    idx, object['set_idx'])
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_SCORE', {
                        'teamid': idx + 1,
                        'setid': object['set_idx'] + 1,
                        'color': color})

            set_idx = self.matchData.getNextSet(True)

            file = 'src/img/races/{}.png'

            for idx in range(1):
                img = file.format(self.matchData.getRace(
                    idx, set_idx).replace(' ', '_'))
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_IMAGE',
                    {'id': 'logo{}'.format(idx + 1), 'img': img})

            self.updatePlayerIntros()
        elif label == 'color':
            for idx in range(2):
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_SCORE', {
                        'teamid': idx + 1,
                        'setid': object['set_idx'] + 1,
                        'color': object['score_color']})
        elif label == 'outcome':
            self.websocketThread.sendData2Path('score', 'SET_WINNER', object)
        elif label == 'player':
            if object['set_idx'] == 0 and self.matchData.getSolo():
                self.websocketThread.sendData2Path(
                    'score', 'CHANGE_TEXT',
                    {'id': 'team{}'.format(object['team_idx'] + 1),
                     'text': object['value']})
            if object['set_idx'] == self.matchData.getNextSet(True):
                self.updatePlayerIntros()
        elif label == 'race':

            set_idx = self.matchData.getNextSet(True)

            if object['set_idx'] == set_idx:
                self.updatePlayerIntros()
                file = 'src/img/races/{}.png'

                for idx in range(2):
                    img = file.format(self.matchData.getRace(
                        idx, set_idx).replace(' ', '_'))
                    self.websocketThread.sendData2Path(
                        'score', 'CHANGE_IMAGE',
                        {'id': 'logo{}'.format(idx + 1), 'img': img})

    def newVersion(self, version, force=False):
        """Display dialog for new version."""
        prompt = force or hwctool.settings.config.parser.getboolean(
            "SCT", "new_version_prompt")
        if hasattr(sys, "frozen") and prompt:
            messagebox = QMessageBox()
            text = _("A new version {} is available.")
            messagebox.setText(text.format(version))
            messagebox.setInformativeText(_("Update to new version?"))
            messagebox.setWindowTitle(_("New SCC-Tool Version"))
            messagebox.setStandardButtons(
                QMessageBox.Yes | QMessageBox.No)
            messagebox.setDefaultButton(QMessageBox.Yes)
            messagebox.setIcon(QMessageBox.Information)
            messagebox.setWindowModality(Qt.ApplicationModal)
            cb = QCheckBox()
            cb.setChecked(not hwctool.settings.config.parser.getboolean(
                "SCT", "new_version_prompt"))
            cb.setText(_("Don't show on startup."))
            messagebox.setCheckBox(cb)
            if messagebox.exec_() == QMessageBox.Yes:
                ToolUpdater(self, self.view)
            hwctool.settings.config.parser.set("SCT",
                                               "new_version_prompt",
                                               str(not cb.isChecked()))
        else:
            self.view.statusBar().showMessage(
                _("A new version {} is available on GitHub!").format(version))
