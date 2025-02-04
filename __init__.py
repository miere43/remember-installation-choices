import os
import re
import shutil
import json
import mobase
from typing import Dict, Iterable, List, TypeVar, cast, Optional, Union
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

def makeSavePathV3(organizer: mobase.IOrganizer, modName: str) -> str:
    return os.path.join(getSavesV3Folder(organizer), escapeFileName(modName) + ".json")

def getSavesV3Folder(organizer: mobase.IOrganizer) -> str:
    return os.path.join(
        os.path.join(
            organizer.pluginDataPath(),
            "RememberInstallationChoices",
        ),
        "saves_v3",
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
        newPath = makeSavePathV3(organizer, modName)
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
        # automatic version replacement, see 'scripts/make_build.py'
        # VERSION_BEGIN
        return mobase.VersionInfo(1, 2, 1, 0)
        # VERSION_END

    def _setting(self, key: str) -> object:
        return self._organizer.pluginSetting(self.name(), key)

    def isActive(self) -> bool:
        return bool(self._setting("enabled"))

    def previousChoiceStyleSheet(self) -> str:
        return str(self._setting("previous_choice_style_sheet"))

    def disabledPreviousChoiceStyleSheet(self) -> str:
        return str(self._setting("previous_choice_disabled_style_sheet"))

    def hintChoiceStyleSheet(self) -> str:
        return str(self._setting("hint_choice_style_sheet"))

    def disabledHintChoiceStyleSheet(self) -> str:
        return str(self._setting("hint_choice_disabled_style_sheet"))

    def autoSelectPreviousChoices(self) -> bool:
        return bool(self._setting("auto_select_previous_choices"))
    
    def dumpInstallerDialogWidgetTree(self) -> bool:
        return bool(self._setting("xdebug_dump_installer_dialog_widget_tree"))

    def dumpStep(self) -> bool:
        return bool(self._setting("xdebug_dump_step"))

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "enable this plugin", True),
            mobase.PluginSetting("previous_choice_style_sheet", "Style sheet to apply to clickable choices", "background-color: rgba(0, 255, 0, 0.25)"),
            mobase.PluginSetting("previous_choice_disabled_style_sheet", "Style sheet to apply to unclickable choices", "background-color: rgba(0, 255, 0, 0.15)"),
            mobase.PluginSetting("hint_choice_style_sheet", "Style sheet to apply to clickable choices", "background-color: rgba(255, 255, 0, 0.25)"),
            mobase.PluginSetting("hint_choice_disabled_style_sheet", "Style sheet to apply to unclickable choices", "background-color: rgba(255, 255, 0, 0.15)"),
            mobase.PluginSetting("auto_select_previous_choices", "Automatically selects previous choices", False),
            mobase.PluginSetting("xdebug_dump_installer_dialog_widget_tree", "", False),
            mobase.PluginSetting("xdebug_dump_step", "", False),
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

def dumpChildrenWriteFile(obj: QObject):
    with open(os.path.join(currentFileFolder, "debug_dump_children.json"), "w") as file:
        json.dump(dumpChildren(obj, obj), file, indent=4)

def dumpChildren(obj: QObject, rootObj: QObject) -> List[Dict[str, object]]:
    root = []
    for child in obj.children():
        data: Dict[str, object] = {
            "object": str(child.__class__.__name__),
            "objectName": child.objectName(),
        }

        if isinstance(child, QWidget) and isinstance(rootObj, QWidget):
            data["isVisible"] = child.isVisibleTo(rootObj)

        if isinstance(child, (QRadioButton, QPushButton, QCheckBox)):
            data["text"] = child.text()
        elif isinstance(child, QGroupBox):
            data["title"] = child.title()
        
        data["children"] = dumpChildren(child, rootObj)
        root.append(data)
    return root

T = TypeVar('T', "FomodGroupSave", "FomodStepSave", "FomodChoiceSave")
def findWidgetListObject(
    objects: List[T],
    objectName: str,
    title: str,
    wantedWidgetIndex: int
) -> Optional[T]:
    matchingObjects: List[T] = []
    for object in objects:
        if object.getText() == title:
            matchingObjects.append(object)
    
    if len(matchingObjects) <= 1:
        return matchingObjects[0] if matchingObjects else None

    logDebug(f"Found multiple {objectName}s with same title '{title}', will try to disambiguate them using wantedWidgetIndex={wantedWidgetIndex}")
    for object in matchingObjects:
        logDebug(f"- Got group with index={object.widgetIndex}")
        if object.widgetIndex == wantedWidgetIndex:
            return object

    logCritical(f"There are multiple {objectName}s with same name '{title}', couldn't disambiguate between them, choices for this {objectName} probably will be incorrect")
    return matchingObjects[0]

class FomodChoiceSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.text = ""
        self.widgetIndex = -1
        self.isChecked = False
        
        if isinstance(save, dict):
            self.text = str(save["text"])
            
            widgetIndex = save.get("widgetIndex", -1)
            if isinstance(widgetIndex, int):
                self.widgetIndex = widgetIndex

            self.isChecked = bool(save["isChecked"])

    def getText(self) -> str:
        return self.text

    def toDict(self) -> Dict[str, object]:
        return {
            "text": self.text,
            "widgetIndex": self.widgetIndex,
            "isChecked": self.isChecked,
        }

class FomodGroupSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.title = ""
        self.widgetIndex: int = -1
        self.choices: List[FomodChoiceSave] = []
        
        if isinstance(save, dict):
            self.title = str(save["title"])
            for choice in cast(Iterable, save["choices"]):
                self.choices.append(FomodChoiceSave(choice))
            widgetIndex = save.get("widgetIndex", -1)
            if isinstance(widgetIndex, int):
                self.widgetIndex = widgetIndex

    def getText(self) -> str:
        return self.title

    def findChoice(self, text: str, wantedWidgetIndex: int) -> Optional[FomodChoiceSave]:
        return findWidgetListObject(self.choices, 'choice', text, wantedWidgetIndex)

    def toDict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "widgetIndex": self.widgetIndex,
            "choices": list(map(lambda x: x.toDict(), self.choices)),
        }

class FomodStepSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.title: str = ""
        self.widgetIndex: int = -1
        self.groups: List[FomodGroupSave] = []
  
        if isinstance(save, dict):
            self.title = str(save["title"])
            for group in cast(Iterable, save["groups"]):
                self.groups.append(FomodGroupSave(group))
            widgetIndex = save.get("widgetIndex", -1)
            if isinstance(widgetIndex, int):
                self.widgetIndex = widgetIndex

    def getText(self) -> str:
        return self.title

    def findGroup(self, title: str, wantedWidgetIndex: int) -> Optional[FomodGroupSave]:
        return findWidgetListObject(self.groups, 'group', title, wantedWidgetIndex)

    def toDict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "widgetIndex": self.widgetIndex,
            "groups": list(map(lambda x: x.toDict(), self.groups)),
        }

class FomodSave():
    def __init__(self, save: Optional[Dict[str, object]] = None):
        self.steps: List[FomodStepSave] = []
  
        if isinstance(save, dict):
            for group in cast(Iterable, save["steps"]):
                self.steps.append(FomodStepSave(group))

    def findStep(self, title: str, wantedWidgetIndex: int) -> Optional[FomodStepSave]:
        return findWidgetListObject(self.steps, 'step', title, wantedWidgetIndex)
    
    def upsertStep(self, newStep: FomodStepSave) -> None:
        for index, step in enumerate(self.steps):
            if step.title == newStep.title and (step.widgetIndex == newStep.widgetIndex or step.widgetIndex == -1):
                self.steps[index] = newStep
                return
        self.steps.append(newStep)

    def toDict(self) -> Dict[str, object]:
        return {
            "steps": list(map(lambda x: x.toDict(), self.steps)),
        }

class FomodChoice():
    def __init__(self, plugin: RememberModChoicesPlugin, widget: Union[QRadioButton, QCheckBox], widgetIndex: int):
        self.plugin = plugin
        self.widget = widget
        self.widget.toggled.connect(self._updateVisuals)
        self.widgetIndex = widgetIndex
        self.originalToolTip = self.widget.toolTip()
        self.save: Optional[FomodChoiceSave] = None

    def text(self) -> str:
        return self.widget.text()
    
    def isChecked(self) -> bool:
        return self.widget.isChecked()
    
    def setChecked(self, checked: bool) -> None:
        if self.widget.isEnabled():
            self.widget.setChecked(checked)
            self._updateVisuals()

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
    def __init__(self, groupBox: QGroupBox, widgetIndex: int):
        self.groupBox = groupBox
        self.choices: List[FomodChoice] = []
        self.widgetIndex = widgetIndex

    def title(self) -> str:
        return self.groupBox.title()
    
    def _destroy(self) -> None:
        for choice in self.choices:
            choice._destroy()

class FomodStep():
    def __init__(self):
        self.title = ""
        self.groups: List[FomodGroup] = []
        self.widgetIndex = -1

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
        if plugin.dumpInstallerDialogWidgetTree():
            dumpChildrenWriteFile(self.widget)
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

        path = makeSavePathV3(self.plugin._organizer, self.modName)
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
        
        savePath = makeSavePathV3(self.plugin._organizer, self.modName)
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
        saveStep.widgetIndex = self.currentStep.widgetIndex
        self.updatedSaveData.upsertStep(saveStep)

        for group in self.currentStep.groups:
            saveGroup = FomodGroupSave()
            saveGroup.title = group.title()
            saveGroup.widgetIndex = group.widgetIndex
            for choice in group.choices:
                saveChoice = FomodChoiceSave()
                saveChoice.text = choice.text()
                saveChoice.widgetIndex = choice.widgetIndex
                saveChoice.isChecked = choice.isChecked()
                saveGroup.choices.append(saveChoice)
            saveStep.groups.append(saveGroup)

    def loadStepAndApplySaveState(self) -> None:
        self.loadStep()
        if not self.currentStep or not self.saveData:
            return

        saveStep = self.saveData.findStep(self.currentStep.title, self.currentStep.widgetIndex)
        if not saveStep:
            return
        
        for group in self.currentStep.groups:
            saveGroup = saveStep.findGroup(group.title(), group.widgetIndex)
            if saveGroup == None:
                continue

            for choice in group.choices:
                if saveChoice := saveGroup.findChoice(choice.text(), choice.widgetIndex):
                    choice.setSave(saveChoice)
                    if self.plugin.autoSelectPreviousChoices():
                        choice.setChecked(saveChoice.isChecked)

    def loadStep(self) -> None:
        if self.currentStep:
            self.currentStep._destroy()

        self.currentStep = FomodStep()

        stepsStack = self.widget.findChild(QStackedWidget, "stepsStack")
        if not stepsStack:
            logCritical(f"Failed to find 'stepsStack' widget")
            return
        
        self.currentStep.widgetIndex = stepsStack.currentIndex()
        if self.currentStep.widgetIndex == -1:
            logCritical(f"'stepsStack' widget must have current index, but it was -1")
        
        visibleStepWidget: Optional[QGroupBox] = None
        for stepWidget in stepsStack.children():
            if isinstance(stepWidget, QGroupBox) and stepWidget.isVisibleTo(self.widget):
                visibleStepWidget = stepWidget
                break

        if not visibleStepWidget:
            logCritical(f"Failed to find visible step widget")
            return
        
        self.currentStep.title = visibleStepWidget.title()
        for index, groupBox in enumerate(visibleStepWidget.findChildren(QGroupBox, None)):
            group = FomodGroup(groupBox, index)
            self.currentStep.groups.append(group)

            for index, choiceWidget in enumerate(groupBox.children()):
                if isinstance(choiceWidget, (QCheckBox, QRadioButton)) and choiceWidget.objectName() in ("choice", "none"): 
                    group.choices.append(FomodChoice(self.plugin, choiceWidget, index))
    
        if self.plugin.dumpStep():
            dumpStep(self.currentStep)

def dumpStep(step: FomodStep) -> None:
    logCritical(f"Step title: '{step.title}', widget index: {step.widgetIndex}")
    for group in step.groups:
        logCritical(f"Group: '{group.title()}', widget index: {group.widgetIndex}")
        for choice in group.choices:
            logCritical(f"- Choice: '{choice.text()}, checked: {choice.isChecked()}, widget index: {choice.widgetIndex}'")

def createPlugin() -> mobase.IPlugin:
    return RememberModChoicesPlugin()
