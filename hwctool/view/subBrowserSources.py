"""Show connections settings sub window."""
import logging

import gtts
import keyboard
from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QShortcut, QSizePolicy, QSlider,
                             QSpacerItem, QTabWidget, QVBoxLayout, QWidget)

import hwctool.settings
from hwctool.view.widgets import HotkeyLayout, StyleComboBox

# create logger
module_logger = logging.getLogger('hwctool.view.subConnections')


class SubwindowBrowserSources(QWidget):
    """Show connections settings sub window."""

    def createWindow(self, mainWindow, tab=''):
        """Create window."""
        try:
            parent = None
            super().__init__(parent)
            # self.setWindowFlags(Qt.WindowStaysOnTopHint)

            self.setWindowIcon(
                QIcon(hwctool.settings.getResFile('browser.png')))
            self.setWindowModality(Qt.ApplicationModal)
            self.mainWindow = mainWindow
            self.passEvent = False
            self.controller = mainWindow.controller
            self.__dataChanged = False

            self.createButtonGroup()
            self.createTabs(tab)

            mainLayout = QVBoxLayout()

            mainLayout.addWidget(self.tabs)
            mainLayout.addLayout(self.buttonGroup)

            self.setLayout(mainLayout)

            self.resize(QSize(mainWindow.size().width() * 0.8,
                              self.sizeHint().height()))
            relativeChange = QPoint(mainWindow.size().width() / 2,
                                    mainWindow.size().height() / 3) -\
                QPoint(self.size().width() / 2,
                       self.size().height() / 3)
            self.move(mainWindow.pos() + relativeChange)

            self.setWindowTitle(_("Browser Sources"))

        except Exception as e:
            module_logger.exception("message")

    def createTabs(self, tab):
        """Create tabs."""
        self.tabs = QTabWidget()

        self.createFormGroupIntro()

        # Add tabs
        self.tabs.addTab(self.formGroupIntro, _("Intros"))
        table = dict()
        table['intro'] = 0
        self.tabs.setCurrentIndex(table.get(tab, -1))

    def addHotkey(self, ident, label):
        element = HotkeyLayout(
            self, ident, label,
            hwctool.settings.config.parser.get("Intros", ident))
        self.hotkeys[ident] = element
        return element

    def connectHotkeys(self):
        for ident, key in self.hotkeys.items():
            if ident == 'hotkey_debug':
                for ident2, key2 in self.hotkeys.items():
                    if ident == ident2:
                        continue
                    key.modified.connect(key2.check_dublicate)
            key.modified.connect(self.hotkeyChanged)

    def hotkeyChanged(self, key, ident):
        self.changed()

        if(ident == 'hotkey_player1' and self.cb_single_hotkey.isChecked()):
            self.hotkeys['hotkey_player2'].setData(
                self.hotkeys['hotkey_player1'].getKey())

        if not key:
            return

        if((ident == 'hotkey_player1' and
            key == self.hotkeys['hotkey_player2'].getKey()['name']) or
           (ident == 'hotkey_player2' and
                key == self.hotkeys['hotkey_player1'].getKey()['name'])):
            self.cb_single_hotkey.setChecked(True)

        if(ident in ['hotkey_player1', 'hotkey_player2'] and
           key == self.hotkeys['hotkey_debug'].getKey()['name']):
            self.hotkeys['hotkey_debug'].clear()

    def singleHotkeyChanged(self):
        checked = self.cb_single_hotkey.isChecked()
        self.hotkeys['hotkey_player2'].setDisabled(checked)
        if checked:
            self.hotkeys['hotkey_player2'].setData(
                self.hotkeys['hotkey_player1'].getKey())
        elif(self.hotkeys['hotkey_player1'].getKey() ==
             self.hotkeys['hotkey_player2'].getKey()):
            self.hotkeys['hotkey_player2'].clear()

    def createFormGroupIntro(self):
        """Create forms for websocket connection to intro."""
        self.formGroupIntro = QWidget()
        mainLayout = QVBoxLayout()

        box = QGroupBox(_("Style"))
        layout = QHBoxLayout()
        styleqb = StyleComboBox(
            hwctool.settings.casting_html_dir + "/src/css/intro",
            "intro")
        styleqb.connect2WS(self.controller, 'intro')
        button = QPushButton(_("Show in Browser"))
        button.clicked.connect(lambda: self.openHTML(
            hwctool.settings.casting_html_dir + "/intro.html"))
        layout.addWidget(styleqb, 2)
        layout.addWidget(button, 1)
        box.setLayout(layout)
        mainLayout.addWidget(box)

        self.hotkeyBox = QGroupBox(_("Hotkeys"))
        layout = QVBoxLayout()
        try:
            keyboard.unhook_all()
        except AttributeError:
            pass

        self.cb_single_hotkey = QCheckBox(
            _("Use a single hotkey for both players"))
        self.cb_single_hotkey.stateChanged.connect(self.singleHotkeyChanged)
        layout.addWidget(self.cb_single_hotkey)

        self.hotkeys = dict()
        layout.addLayout(self.addHotkey("hotkey_player1", _("Player 1")))
        layout.addLayout(self.addHotkey("hotkey_player2", _("Player 2")))
        layout.addLayout(self.addHotkey("hotkey_debug", _("Debug")))

        self.cb_single_hotkey.setChecked(
            self.hotkeys['hotkey_player1'].getKey() ==
            self.hotkeys['hotkey_player2'].getKey())
        self.connectHotkeys()
        label = QLabel(_("Player 1 is always the player your observer"
                         " camera is centered on at start of a game."))
        layout.addWidget(label)
        self.hotkeyBox.setLayout(layout)
        mainLayout.addWidget(self.hotkeyBox)

        self.introBox = QGroupBox(_("Animation"))
        layout = QFormLayout()
        self.cb_animation = QComboBox()
        animation = hwctool.settings.config.parser.get("Intros", "animation")
        currentIdx = 0
        idx = 0
        options = dict()
        options['Fly-In'] = _("Fly-In")
        options['Slide'] = _("Slide")
        options['Fanfare'] = _("Fanfare")
        for key, item in options.items():
            self.cb_animation.addItem(item, key)
            if(key == animation):
                currentIdx = idx
            idx += 1
        self.cb_animation.setCurrentIndex(currentIdx)
        self.cb_animation.currentIndexChanged.connect(self.changed)
        label = QLabel(_("Animation:") + " ")
        label.setMinimumWidth(120)
        layout.addRow(label, self.cb_animation)
        self.sb_displaytime = QDoubleSpinBox()
        self.sb_displaytime.setRange(0, 10)
        self.sb_displaytime.setDecimals(1)
        self.sb_displaytime.setValue(
            hwctool.settings.config.parser.getfloat("Intros", "display_time"))
        self.sb_displaytime.setSuffix(" " + _("Seconds"))
        self.sb_displaytime.valueChanged.connect(self.changed)
        layout.addRow(QLabel(
            _("Display Duration:") + " "), self.sb_displaytime)
        self.sl_sound = QSlider(Qt.Horizontal)
        self.sl_sound.setMinimum(0)
        self.sl_sound.setMaximum(20)
        self.sl_sound.setValue(
            hwctool.settings.config.parser.getint("Intros", "sound_volume"))
        self.sl_sound.setTickPosition(QSlider.TicksBothSides)
        self.sl_sound.setTickInterval(1)
        self.sl_sound.valueChanged.connect(self.changed)
        layout.addRow(QLabel(
            _("Sound Volume:") + " "), self.sl_sound)
        self.introBox.setLayout(layout)
        mainLayout.addWidget(self.introBox)

        self.ttsBox = QGroupBox(_("Text-to-Speech"))
        layout = QFormLayout()

        self.cb_tts_active = QCheckBox()
        self.cb_tts_active.setChecked(
            hwctool.settings.config.parser.getboolean("Intros", "tts_active"))
        self.cb_tts_active.stateChanged.connect(self.changed)
        label = QLabel(_("Activate Text-to-Speech:") + " ")
        label.setMinimumWidth(120)
        layout.addRow(label, self.cb_tts_active)

        self.cb_tts_lang = QComboBox()

        currentIdx = 0
        idx = 0
        tts_langs = gtts.lang.tts_langs()
        tts_lang = hwctool.settings.config.parser.get("Intros", "tts_lang")
        for key, name in tts_langs.items():
            self.cb_tts_lang.addItem(name, key)
            if(key == tts_lang):
                currentIdx = idx
            idx += 1
        self.cb_tts_lang.setCurrentIndex(currentIdx)
        self.cb_tts_lang.currentIndexChanged.connect(self.changed)
        layout.addRow(QLabel(
            _("Language:") + " "), self.cb_tts_lang)
        self.ttsBox.setStyleSheet("QComboBox { combobox-popup: 0; }")
        self.ttsBox.setLayout(layout)
        mainLayout.addWidget(self.ttsBox)

        self.cb_tts_scope = QComboBox()
        scope = hwctool.settings.config.parser.get("Intros", "tts_scope")
        currentIdx = 0
        idx = 0
        options = dict()
        options['team_player'] = _("Team & Player")
        options['player'] = _("Player")
        for key, item in options.items():
            self.cb_tts_scope.addItem(item, key)
            if(key == scope):
                currentIdx = idx
            idx += 1
        self.cb_tts_scope.setCurrentIndex(currentIdx)
        self.cb_tts_scope.currentIndexChanged.connect(self.changed)
        layout.addRow(QLabel(
            _("Scope:") + " "), self.cb_tts_scope)

        self.sl_tts_sound = QSlider(Qt.Horizontal)
        self.sl_tts_sound.setMinimum(0)
        self.sl_tts_sound.setMaximum(20)
        self.sl_tts_sound.setValue(
            hwctool.settings.config.parser.getint("Intros", "tts_volume"))
        self.sl_tts_sound.setTickPosition(QSlider.TicksBothSides)
        self.sl_tts_sound.setTickInterval(1)
        self.sl_tts_sound.valueChanged.connect(self.changed)
        layout.addRow(QLabel(
            _("Sound Volume:") + " "), self.sl_tts_sound)

        mainLayout.addItem(QSpacerItem(
            0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.formGroupIntro.setLayout(mainLayout)

    def createButtonGroup(self):
        """Create buttons."""
        try:
            layout = QHBoxLayout()

            layout.addWidget(QLabel(""))

            buttonCancel = QPushButton(_('Cancel'))
            buttonCancel.clicked.connect(self.closeWindow)
            layout.addWidget(buttonCancel)

            buttonSave = QPushButton(_('&Save && Close'))
            buttonSave.setToolTip(_("Shortcut: {}").format("Ctrl+S"))
            self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
            self.shortcut.setAutoRepeat(False)
            self.shortcut.activated.connect(self.saveCloseWindow)
            buttonSave.clicked.connect(self.saveCloseWindow)
            layout.addWidget(buttonSave)

            self.buttonGroup = layout
        except Exception as e:
            module_logger.exception("message")

    def changed(self, *values):
        """Handle changed data."""
        self.__dataChanged = True

    def saveData(self):
        """Save the data to config."""
        if(self.__dataChanged):
            self.saveWebsocketdata()
            self.__dataChanged = False
            # self.controller.refreshButtonStatus()

    def saveWebsocketdata(self):
        """Save Websocket data."""
        for ident, key in self.hotkeys.items():
            string = hwctool.settings.config.dumpHotkey(key.getKey())
            hwctool.settings.config.parser.set("Intros", ident, string)
        hwctool.settings.config.parser.set(
            "Intros", "display_time", str(self.sb_displaytime.value()))
        hwctool.settings.config.parser.set(
            "Intros", "sound_volume", str(self.sl_sound.value()))
        hwctool.settings.config.parser.set(
            "Intros", "animation", self.cb_animation.currentData().strip())
        hwctool.settings.config.parser.set(
            "Intros", "tts_lang", self.cb_tts_lang.currentData().strip())
        hwctool.settings.config.parser.set(
            "Intros", "tts_scope", self.cb_tts_scope.currentData().strip())
        hwctool.settings.config.parser.set(
            "Intros", "tts_active", str(self.cb_tts_active.isChecked()))
        hwctool.settings.config.parser.set(
            "Intros", "tts_volume", str(self.sl_tts_sound.value()))

    def openHTML(self, file):
        """Open file in browser."""
        self.controller.openURL(hwctool.settings.getAbsPath(file))

    def saveCloseWindow(self):
        """Save and close window."""
        self.saveData()
        self.closeWindow()

    def closeWindow(self):
        """Close window without save."""
        self.passEvent = True
        self.close()

    def closeEvent(self, event):
        """Handle close event."""
        try:
            if(not self.__dataChanged):
                event.accept()
                return
            if(not self.passEvent):
                if(self.isMinimized()):
                    self.showNormal()
                buttonReply = QMessageBox.question(
                    self, _('Save data?'), _("Do you want to save the data?"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No)
                if buttonReply == QMessageBox.Yes:
                    self.saveData()
            self.controller.updateHotkeys()
            event.accept()
        except Exception as e:
            module_logger.exception("message")
