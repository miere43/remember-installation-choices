import os
import re
import shutil
import json
import mobase
from typing import Dict, Iterable, List, cast, Optional, Union
try:
    from PyQt6.QtWidgets import QMainWindow, QGroupBox, QStackedWidget, QWidget, QApplication, QRadioButton, QPushButton, QCheckBox, QComboBox
    from PyQt6.QtCore import QObject, qInfo, qDebug, qWarning, qCritical
    from PyQt6.QtGui import QWindow, QGuiApplication
except ImportError:
    from PyQt5.QtWidgets import QMainWindow, QGroupBox, QStackedWidget, QWidget, QApplication, QRadioButton, QPushButton, QCheckBox, QComboBox
    from PyQt5.QtCore import QObject, qInfo, qDebug, qWarning, qCritical
    from PyQt5.QtGui import QWindow, QGuiApplication

currentFileFolder = os.path.dirname(os.path.realpath(__file__))

def logInfo(s: str) -> None:
    qInfo(f"[Remember Installation Choices] {s}")

def logDebug(s: str) -> None:
    qDebug(f"[Remember Installation Choices] {s}")

def logCritical(s: str) -> None:
    qCritical(f"[Remember Installation Choices] {s}")

def logWarning(s: str) -> None:
    qWarning(f"[Remember Installation Choices] {s}")

def escapeFileName(fileName: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', fileName)

def getSavesV1Folder(organizer: mobase.IOrganizer) -> str:
    return os.path.join(
        currentFileFolder,
        "saves",
        escapeFileName(organizer.managedGame().gameName()),
    )

def makeSavePathV1(organizer: mobase.IOrganizer, modName: str) -> str:
    return os.path.join(
        getSavesV1Folder(organizer),
        escapeFileName(organizer.profileName()),
        escapeFileName(modName) + ".json",
    )

def makeSavePathV2(organizer: mobase.IOrganizer, modName: str) -> str:
    return os.path.join(getSavesV2Folder(organizer), escapeFileName(modName) + ".json")

def getSavesV2Folder(organizer: mobase.IOrganizer) -> str:
    return os.path.join(
        currentFileFolder,
        "saves_v2",
        escapeFileName(organizer.managedGame().gameName()),
    )

def getFilePathsInFolder(folderPath: str, extension: str) -> List[str]:
    filePaths: List[str] = []
    for root, _, files in os.walk(folderPath):
        for file in files:
            if file.endswith(extension):
                filePaths.append(os.path.join(root, file))
    return filePaths

def migrateSavesV1(organizer: mobase.IOrganizer) -> None:
    oldSaveFolder = os.path.join(currentFileFolder, "saves")
    oldPaths = getFilePathsInFolder(oldSaveFolder, ".json")
    if len(oldPaths) == 0:
        logDebug("migrateSavesV1: no old saves were found, skipping migration")
        return
    
    logInfo(f"Detected {len(oldPaths)} old saves, will migrate to new version")
    
    backupDir = os.path.join(currentFileFolder, "saves_backup")
    shutil.copytree(oldSaveFolder, backupDir, dirs_exist_ok=True)
    logInfo(f"Created backup saves at '{backupDir}'")

    os.makedirs(getSavesV2Folder(organizer), exist_ok=True)
    for oldPath in oldPaths:
        oldPathShort = os.path.relpath(oldPath, currentFileFolder)
        oldModTime = os.path.getmtime(oldPath)

        modName, _ = os.path.splitext(os.path.basename(oldPath))
        newPath = makeSavePathV2(organizer, modName)
        newPathShort = os.path.relpath(newPath, currentFileFolder)
        newModTime = os.path.getmtime(newPath) if os.path.exists(newPath) else 0

        if newModTime >= oldModTime:
            os.remove(oldPath)
            logDebug(f"Removed old save '{oldPathShort}' with modtime={oldModTime}, because there is newer save at '{newPathShort}' with modtime={newModTime}")
        else:
            shutil.move(oldPath, newPath)
            logDebug(f"Moved old save '{oldPathShort}' with modtime={oldModTime} to path '{newPathShort}' (this file had modtime={newModTime}), because old save is newer or new save does not exist")
    logInfo("Save migration complete")

class RememberModChoicesPlugin(mobase.IPlugin):
    def __init__(self):
        super().__init__()
        self.currentDialog: Optional[FomodInstallerDialog] = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        organizer.onUserInterfaceInitialized(lambda a: self._onUserInterfaceInitialized(a))
        return True

    def name(self) -> str:
        return "Remember Installation Choices"

    def author(self) -> str:
        return "miere"

    def description(self) -> str:
        return "Saves choices you made during mod installation, and shows them next time you reinstall the mod."

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 1, 0, 0)

    def isActive(self) -> bool:
        return bool(self._organizer.pluginSetting(self.name(), "enabled"))

    def previousChoiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "previous_choice_style_sheet"))

    def disabledPreviousChoiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "previous_choice_disabled_style_sheet"))

    def hintChoiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "hint_choice_style_sheet"))

    def disabledHintChoiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "hint_choice_disabled_style_sheet"))

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "enable this plugin", True),
            mobase.PluginSetting("previous_choice_style_sheet", "Style sheet to apply to clickable choices", "background-color: rgba(0, 255, 0, 0.25)"),
            mobase.PluginSetting("previous_choice_disabled_style_sheet", "Style sheet to apply to unclickable choices", "background-color: rgba(0, 255, 0, 0.15)"),
            mobase.PluginSetting("hint_choice_style_sheet", "Style sheet to apply to clickable choices", "background-color: rgba(255, 255, 0, 0.25)"),
            mobase.PluginSetting("hint_choice_disabled_style_sheet", "Style sheet to apply to unclickable choices", "background-color: rgba(255, 255, 0, 0.15)"),
        ]
    
    def _onUserInterfaceInitialized(self, mainWindow: QMainWindow):
        try:
            migrateSavesV1(self._organizer)
        except Exception as e:
            logCritical(f"Failed to migrate old saves: {e}")

        app = QApplication.instance()
        if app and isinstance(app, QGuiApplication):
            app.focusWindowChanged.connect(self._focusWindowChanged)

    def _focusWindowChanged(self, window: Optional[QWindow]):
        if window != None:
            self._findInstallerDialog()

    def _findInstallerDialog(self):
        if self.currentDialog:
            return

        for widget in QApplication.topLevelWidgets():
            if widget.objectName() == "FomodInstallerDialog":
                self.currentDialog = FomodInstallerDialog(self, widget)
                logDebug(f"Found install window {widget}")
                break

# def dumpChildrenWriteFile(obj: QObject):
#     with open(os.path.join(currentFileFolder, "debug_dump_children.json"), "w") as file:
#         json.dump(dumpChildren(obj, obj), file, indent=4)

def dumpChildren(obj: QObject, rootObj: QObject) -> List[Dict[str, object]]:
    root = []
    for child in obj.children():
        data: Dict[str, object] = {
            "object": str(child.__class__.__name__),
            "objectName": child.objectName(),
        }

        if isinstance(child, QWidget) and isinstance(rootObj, QWidget):
            data["isVisible"] = child.isVisibleTo(rootObj)

        if isinstance(child, QRadioButton):
            data["text"] = child.text()
        elif isinstance(child, QGroupBox):
            data["title"]= child.title()
        elif isinstance(child, QPushButton):
            data["text"] = child.text()
        elif isinstance(child, QCheckBox):
            data["text"] = child.text()
        
        data["children"] = dumpChildren(child, rootObj)
        root.append(data)
    return root

class FomodChoiceSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.text = ""
        self.isChecked = False
        
        if isinstance(save, dict):
            self.text = str(save["text"])
            self.isChecked = bool(save["isChecked"])

    def toDict(self) -> Dict[str, object]:
        return {
            "text": self.text,
            "isChecked": self.isChecked,
        }

class FomodGroupSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.title = ""
        self.choices: List[FomodChoiceSave] = []
        
        if isinstance(save, dict):
            self.title = save["title"]
            for choice in cast(Iterable, save["choices"]):
                self.choices.append(FomodChoiceSave(choice))

    def choiceByText(self, text: str) -> Optional[FomodChoiceSave]:
        for choice in self.choices:
            if choice.text == text:
                return choice
        return None

    def toDict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "choices": list(map(lambda x: x.toDict(), self.choices)),
        }

class FomodStepSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.title = ""
        self.groups: List[FomodGroupSave] = []
  
        if isinstance(save, dict):
            self.title = str(save["title"])
            for group in cast(Iterable, save["groups"]):
                self.groups.append(FomodGroupSave(group))

    def groupByTitle(self, title: str) -> Optional[FomodGroupSave]:
        for group in self.groups:
            if group.title == title:
                return group
        return None

    def toDict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "groups": list(map(lambda x: x.toDict(), self.groups)),
        }

class FomodSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.steps: List[FomodStepSave] = []
  
        if isinstance(save, dict):
            for group in cast(Iterable, save["steps"]):
                self.steps.append(FomodStepSave(group))

    def stepByTitle(self, title: str) -> Optional[FomodStepSave]:
        for step in self.steps:
            if step.title == title:
                return step
        return None
    
    def upsertStep(self, newStep: FomodStepSave) -> None:
        for index, step in enumerate(self.steps):
            if step.title == newStep.title:
                self.steps[index] = newStep
                return
        self.steps.append(newStep)

    def toDict(self) -> Dict[str, object]:
        return {
            "steps": list(map(lambda x: x.toDict(), self.steps)),
        }

class FomodChoice():
    def __init__(self, plugin: RememberModChoicesPlugin, widget: Union[QRadioButton, QCheckBox]):
        self.plugin = plugin
        self.widget = widget
        self.widget.toggled.connect(self._updateVisuals)
        self.originalToolTip = self.widget.toolTip()
        self.save: Optional[FomodChoiceSave] = None

    def text(self) -> str:
        return self.widget.text()
    
    def isChecked(self) -> bool:
        return self.widget.isChecked()
    
    def _makeToolTipText(self, text) -> str:
        return f"{text}\n\n{self.originalToolTip}".strip()

    def _usePreviousChoiceVisuals(self) -> None:
        self.widget.setToolTip(self._makeToolTipText("You previously selected this choice when you installed this mod."))
        styleSheet = self.plugin.previousChoiceStyleSheet() if self.widget.isEnabled() else self.plugin.disabledPreviousChoiceStyleSheet()
        self.widget.setStyleSheet(f"{self.widget.__class__.__name__} {{ {styleSheet} }}")

    def _useHintVisuals(self) -> None:
        self.widget.setToolTip(self._makeToolTipText("This choice doesn't match your previous choice when you installed this mod."))
        styleSheet = self.plugin.hintChoiceStyleSheet() if self.widget.isEnabled() else self.plugin.disabledHintChoiceStyleSheet()
        self.widget.setStyleSheet(f"{self.widget.__class__.__name__} {{ {styleSheet} }}")

    def _clearVisuals(self) -> None:
        self.widget.setToolTip(self.originalToolTip)
        self.widget.setStyleSheet(None)

    def setSave(self, save: FomodChoiceSave) -> None:
        self.save = save
        self._updateVisuals()

    def _updateVisuals(self) -> None:
        if self.save and self.save.isChecked and isinstance(self.widget, QRadioButton):
            self._usePreviousChoiceVisuals()
        elif self.save and self.save.isChecked != self.isChecked():
            self._useHintVisuals()
        elif self.save and self.save.isChecked:
            self._usePreviousChoiceVisuals()
        else:
            self._clearVisuals()

    def _destroy(self) -> None:
        self._clearVisuals()
        self.widget.toggled.disconnect(self._updateVisuals)

class FomodGroup():
    def __init__(self, groupBox: QGroupBox):
        self.groupBox = groupBox
        self.choices: List[FomodChoice] = []

    def title(self) -> str:
        return self.groupBox.title()
    
    def _destroy(self) -> None:
        for choice in self.choices:
            choice._destroy()

class FomodStep():
    def __init__(self):
        self.title = ""
        self.groups: List[FomodGroup] = []

    def _destroy(self) -> None:
        for group in self.groups:
            group._destroy()

class FomodInstallerDialog():
    def __init__(self, plugin: RememberModChoicesPlugin, widget: QWidget):
        self.plugin = plugin
        self.widget = widget
        self.widget.destroyed.connect(self.onDestroyed)
        self.destroyed = False
        self.installClicked = False
        self.modName = ''
        self.prevButton = self.widget.findChild(QPushButton, "prevBtn")
        self.nextButton = self.widget.findChild(QPushButton, "nextBtn")
        self.saveData: Optional[FomodSave] = None
        self.updatedSaveData: Optional[FomodSave] = None
        self.currentStep: Optional[FomodStep] = None
        self._nextButtonTextBeforeClick = ''
        # dumpChildrenWriteFile(self.widget)
        self.loadModName()
        self.loadSave()
        self.loadStepAndApplySaveState()
        self.installButtonHandlers()

    def loadModName(self) -> None:
        nameCombo = self.widget.findChild(QComboBox, "nameCombo")
        if not nameCombo:
            self.modName = self.widget.windowTitle()
            logCritical(f"Failed to find nameCombo, using window title as mod name: '{self.modName}'")
            return
        self.modName = nameCombo.currentText()

    def onDestroyed(self) -> None:
        if self.plugin.currentDialog == self:
            self.plugin.currentDialog = None

        if self.destroyed:
            logDebug("FomodInstallerDialog: not saving, window destroy event already handled")
            return
        self.destroyed = True

        if not self.installClicked:
            logDebug("FomodInstallerDialog: not saving, install button was not clicked")
            return

        if not self.updatedSaveData:
            logDebug("FomodInstallerDialog: not saving, save data is missing")
            return

        path = makeSavePathV2(self.plugin._organizer, self.modName)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file:
            json.dump(self.updatedSaveData.toDict(), file, indent=4)
        logDebug(f"FomodInstallerDialog: data saved into '{path}'")

    def installButtonHandlers(self) -> None:
        for button in [self.prevButton, self.nextButton]:
            if not button:
                logCritical(f"Failed to find prev or next button in dialog")
                continue
            button.pressed.connect(self.updateSaveWithCurrentStep)
            button.clicked.connect(self.loadStepAndApplySaveState)

        if self.nextButton:
            self.nextButton.pressed.connect(self._onNextButtonPressed)
            self.nextButton.clicked.connect(self._onNextButtonClicked)

    def _onNextButtonPressed(self) -> None:
        self._nextButtonTextBeforeClick = self.nextButton.text()

    def _onNextButtonClicked(self) -> None:
        if self._nextButtonTextBeforeClick == QApplication.translate("FomodInstallerDialog", "Install"):
            self.installClicked = True
            logDebug(f"onNextButtonClicked installClicked = True")

    def loadSave(self) -> None:
        if self.saveData:
            return
        
        savePath = makeSavePathV2(self.plugin._organizer, self.modName)
        data: Optional[object] = None
        try:
            with open(savePath, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            logDebug(f"No save for '{self.modName}', file path: '{savePath}'")
        except json.JSONDecodeError as e:
            logCritical(f"Failed to decode JSON for file '{savePath}': '{e.msg}'")

        if isinstance(data, dict):
            self.saveData = FomodSave(data)
            self.updatedSaveData = FomodSave(data)

    def updateSaveWithCurrentStep(self) -> None:
        if not self.updatedSaveData:
            self.updatedSaveData = FomodSave()
        if not self.currentStep:
            return

        saveStep = FomodStepSave()
        saveStep.title = self.currentStep.title
        self.updatedSaveData.upsertStep(saveStep)

        for group in self.currentStep.groups:
            saveGroup = FomodGroupSave()
            saveGroup.title = group.title()
            for choice in group.choices:
                saveChoice = FomodChoiceSave()
                saveChoice.text = choice.text()
                saveChoice.isChecked = choice.isChecked()
                saveGroup.choices.append(saveChoice)
            saveStep.groups.append(saveGroup)

    def loadStepAndApplySaveState(self) -> None:
        self.loadStep()
        if not self.currentStep or not self.saveData:
            return

        saveStep = self.saveData.stepByTitle(self.currentStep.title)
        if not saveStep:
            return
        
        for group in self.currentStep.groups:
            saveGroup = saveStep.groupByTitle(group.title())
            if saveGroup == None:
                continue

            for choice in group.choices:
                if saveChoice := saveGroup.choiceByText(choice.text()):
                    choice.setSave(saveChoice)

    def loadStep(self) -> None:
        if self.currentStep:
            self.currentStep._destroy()

        self.currentStep = FomodStep()

        stepsStack = self.widget.findChild(QStackedWidget, "stepsStack")
        
        visibleStepWidget: Optional[QGroupBox] = None
        for stepWidget in stepsStack.children():
            if isinstance(stepWidget, QGroupBox) and stepWidget.isVisibleTo(self.widget):
                visibleStepWidget = stepWidget
                break

        if not visibleStepWidget:
            logCritical(f"Failed to find visible step widget")
            return
        
        self.currentStep.title = visibleStepWidget.title()
        for groupBox in visibleStepWidget.findChildren(QGroupBox, None):
            group = FomodGroup(groupBox)
            self.currentStep.groups.append(group)

            for choice in groupBox.findChildren(QCheckBox, "choice"):
                group.choices.append(FomodChoice(self.plugin, choice))
            for choice in groupBox.findChildren(QRadioButton, "choice"):
                group.choices.append(FomodChoice(self.plugin, choice))
            for choice in groupBox.findChildren(QRadioButton, "none"):
                group.choices.append(FomodChoice(self.plugin, choice))
    
        # dumpStep(self.currentStep)

# def dumpStep(step: FomodStep) -> None:
#     log(f"Step title: '{step.title}'")
#     for group in step.groups:
#         log(f"Group: '{group.title()}'")
#         for choice in group.choices:
#             log(f"- Choice: '{choice.text()}, checked: {choice.isChecked()}'")

def createPlugin() -> mobase.IPlugin:
    return RememberModChoicesPlugin()
