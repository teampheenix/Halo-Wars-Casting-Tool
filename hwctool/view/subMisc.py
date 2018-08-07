"""Show subwindow with miscellaneous settings."""
import logging

from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QHBoxLayout, QInputDialog,
                             QLabel, QMessageBox, QPushButton, QShortcut,
                             QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
                             QWidget)

import hwctool.settings
from hwctool.view.widgets import AliasTreeView, ListTable

# create logger
module_logger = logging.getLogger('hwctool.view.subMisc')


class SubwindowMisc(QWidget):
    """Show subwindow with miscellaneous settings."""

    def createWindow(self, mainWindow, tab=''):
        """Create subwindow with miscellaneous settings."""
        try:
            parent = None
            super().__init__(parent)
            # self.setWindowFlags(Qt.WindowStaysOnTopHint)

            self.setWindowIcon(
                QIcon(hwctool.settings.getResFile('settings.png')))
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

            self.resize(QSize(mainWindow.size().width() * .80,
                              self.sizeHint().height()))
            relativeChange = QPoint(mainWindow.size().width() / 2,
                                    mainWindow.size().height() / 3)\
                - QPoint(self.size().width() / 2,
                         self.size().height() / 3)
            self.move(mainWindow.pos() + relativeChange)

            self.setWindowTitle(_("Miscellaneous Settings"))

        except Exception as e:
            module_logger.exception("message")

    def createTabs(self, tab=''):
        """Create tabs."""
        self.tabs = QTabWidget()

        self.createFavBox()
        self.createAliasBox()

        # Add tabs
        self.tabs.addTab(self.favBox, _("Favorites"))
        self.tabs.addTab(self.aliasBox, _("Alias"))

        table = dict()
        table['favorites'] = 1
        table['alias'] = 2
        self.tabs.setCurrentIndex(table.get(tab, -1))

    def changed(self):
        """Handle changes."""
        self.__dataChanged = True

    def createFavBox(self):
        """Create favorites box."""
        self.favBox = QWidget()
        mainLayout = QVBoxLayout()

        box = QGroupBox(_("Players"))
        layout = QHBoxLayout()

        self.list_favPlayers = ListTable(
            4, hwctool.settings.config.getMyPlayers())
        self.list_favPlayers.dataModified.connect(self.changed)
        self.list_favPlayers.setFixedHeight(150)
        layout.addWidget(self.list_favPlayers)
        box.setLayout(layout)

        mainLayout.addWidget(box)

        mainLayout.addItem(QSpacerItem(
            0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.favBox.setLayout(mainLayout)

    def createAliasBox(self):
        """Create favorites box."""
        self.aliasBox = QWidget()
        mainLayout = QGridLayout()

        aliasDesc = _(
            'Player and team aliases are replaced by the actual name when' +
            ' encountered by the match grabber. Additionally, SC2 player' +
            ' names listed as aliases are replaced in the intros' +
            ' and used to identify players by the automatic' +
            ' background tasks "Auto Score Update" and "Set Ingame Score".')
        label = QLabel(aliasDesc)
        label.setAlignment(Qt.AlignJustify)
        label.setWordWrap(True)

        mainLayout.addWidget(label, 1, 0, 1, 2)

        box = QGroupBox(_("Player Aliases"))
        layout = QVBoxLayout()
        self.list_aliasPlayers = AliasTreeView(self)
        self.list_aliasPlayers.aliasRemoved.connect(
            self.controller.aliasManager.removePlayerAlias)
        layout.addWidget(self.list_aliasPlayers)
        addButton = QPushButton(_("Add Alias"))
        addButton.clicked.connect(lambda: self.addAlias(
            self.list_aliasPlayers, _('Player Name')))
        layout.addWidget(addButton)
        box.setLayout(layout)
        mainLayout.addWidget(box, 0, 0)

        list = self.controller.aliasManager.playerAliasList()
        for player, aliases in list.items():
            self.list_aliasPlayers.insertAliasList(player, aliases)

        list = self.controller.aliasManager.teamAliasList()
        for team, aliases in list.items():
            self.list_aliasTeams.insertAliasList(team, aliases)

        self.aliasBox.setLayout(mainLayout)

    def addAlias(self, widget, scope, name=""):

        name, ok = QInputDialog.getText(
            self, scope, scope + ':', text=name)
        if not ok:
            return

        name = name.strip()
        alias, ok = QInputDialog.getText(
            self, _('Alias'), _('Alias of {}').format(name) + ':', text="")

        alias = alias.strip()
        if not ok:
            return

        try:
            if widget == self.list_aliasPlayers:
                self.controller.aliasManager.addPlayerAlias(name, alias)
            widget.insertAlias(name, alias, True)
        except Exception as e:
            module_logger.exception("message")
            QMessageBox.critical(self, _("Error"), str(e))

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

    def saveData(self):
        """Save the data."""
        if(self.__dataChanged):
            hwctool.settings.config.parser.set(
                "SCT", "commonplayers",
                ", ".join(self.list_favPlayers.getData()))

            self.__dataChanged = False

    def saveCloseWindow(self):
        """Save and close window."""
        self.saveData()
        self.passEvent = True
        self.close()

    def closeWindow(self):
        """Close window."""
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
                    self, _('Save data?'), _("Save data?"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No)
                if buttonReply == QMessageBox.Yes:
                    self.saveData()
            event.accept()
        except Exception as e:
            module_logger.exception("message")
