import os
import re
import sys
import json
import mobase
from typing import Dict, Iterable, List, cast
from PyQt6.QtWidgets import QMainWindow, QGroupBox, QStackedWidget, QWidget, QApplication, QRadioButton, QPushButton, QCheckBox, QComboBox
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QWindow, QGuiApplication

currentFileFolder = os.path.dirname(os.path.realpath(__file__))

def log(s: str) -> None:
    print(s, file=sys.stderr)

class RememberModChoicesPlugin(mobase.IPlugin):
    def __init__(self):
        super().__init__()
        self.currentDialog: FomodInstallerDialog | None = None

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        organizer.onUserInterfaceInitialized(lambda a: self._onUserInterfaceInitialized(a))
        return True

    def name(self) -> str:
        return "Remember mod choices"

    def author(self) -> str:
        return "miere43"

    def description(self) -> str:
        return "Remembers the choices made during mod installation and displays them during the next reinstall."

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.FINAL)

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
        app = QApplication.instance()
        if app and isinstance(app, QGuiApplication):
            app.focusWindowChanged.connect(self._focusWindowChanged)

    def _focusWindowChanged(self, window: QWindow | None):
        log(f"focusWindowChanged to: {window}")
        if window != None:
            self._findInstallerDialog()

    def _findInstallerDialog(self):
        if self.currentDialog:
            return

        for widget in QApplication.topLevelWidgets():
            if widget.objectName() == "FomodInstallerDialog":
                self.currentDialog = FomodInstallerDialog(self, widget)
                log(f"Found install window {widget}")
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
    def __init__(self, save: Dict[str, object] | None = None):
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
    def __init__(self, save: Dict[str, object] | None = None):
        self.title = ""
        self.choices: List[FomodChoiceSave] = []
        
        if isinstance(save, dict):
            self.title = save["title"]
            for choice in cast(Iterable, save["choices"]):
                self.choices.append(FomodChoiceSave(choice))

    def choiceByText(self, text: str) -> FomodChoiceSave | None:
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
    def __init__(self, save: Dict[str, object] | None = None):
        self.title = ""
        self.groups: List[FomodGroupSave] = []
  
        if isinstance(save, dict):
            self.title = str(save["title"])
            for group in cast(Iterable, save["groups"]):
                self.groups.append(FomodGroupSave(group))

    def groupByTitle(self, title: str) -> FomodGroupSave | None:
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
    def __init__(self, save: Dict[str, object] | None = None):
        self.steps: List[FomodStepSave] = []
  
        if isinstance(save, dict):
            for group in cast(Iterable, save["steps"]):
                self.steps.append(FomodStepSave(group))

    def stepByTitle(self, title: str) -> FomodStepSave | None:
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
    def __init__(self, plugin: RememberModChoicesPlugin, widget: QRadioButton | QCheckBox):
        self.plugin = plugin
        self.widget = widget
        self.widget.toggled.connect(self._updateVisuals)
        self.originalToolTip = self.widget.toolTip()
        self.save: FomodChoiceSave | None = None

    def text(self) -> str:
        return self.widget.text()
    
    def isChecked(self) -> bool:
        return self.widget.isChecked()
    
    def _usePreviousChoiceVisuals(self) -> None:
        self.widget.setToolTip("You previously selected this choice when you installed this mod.\n\n" + self.originalToolTip)
        styleSheet = self.plugin.previousChoiceStyleSheet() if self.widget.isEnabled() else self.plugin.disabledPreviousChoiceStyleSheet()
        self.widget.setStyleSheet(f"{self.widget.__class__.__name__} {{ {styleSheet} }}")

    def _useHintVisuals(self) -> None:
        self.widget.setToolTip("This choice doesn't match your previous choice when you installed this mod.\n\n" + self.originalToolTip)
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
        self.prevButton = self.widget.findChild(QPushButton, "prevBtn", Qt.FindChildOption.FindChildrenRecursively)
        self.nextButton = self.widget.findChild(QPushButton, "nextBtn", Qt.FindChildOption.FindChildrenRecursively)
        self.saveData: FomodSave | None = None
        self.updatedSaveData: FomodSave | None = None
        self.currentStep: FomodStep | None = None
        dumpChildrenWriteFile(self.widget)
        self.loadModName()
        self.loadSave()
        self.loadStepAndApplySaveState()
        self.installButtonHandlers()

    def loadModName(self) -> None:
        nameCombo = self.widget.findChild(QComboBox, "nameCombo", Qt.FindChildOption.FindChildrenRecursively)
        if not nameCombo:
            self.modName = self.widget.windowTitle()
            log(f"Failed to find nameCombo, using window title as mod name: '{self.modName}'")
            return
        self.modName = nameCombo.currentText()

    def escapeFileName(self, fileName: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_.-]', '_', fileName)

    def makeSavePath(self) -> str:
        path = os.path.join(
            currentFileFolder,
            "saves",
            self.escapeFileName(self.plugin._organizer.managedGame().gameName()),
            self.escapeFileName(self.plugin._organizer.profileName()),
            self.escapeFileName(self.modName) + ".json",
        )
        log(f"Using save path: {path}")
        return path

    def onDestroyed(self) -> None:
        if self.plugin.currentDialog == self:
            self.plugin.currentDialog = None

        log("FomodInstallerDialog destroyed")

        if self.destroyed:
            log("FomodInstallerDialog: not saving, window destroy event already handled")
            return
        self.destroyed = True

        if not self.installClicked:
            log("FomodInstallerDialog: not saving, install button was not clicked")
            return

        if not self.updatedSaveData:
            log("FomodInstallerDialog: not saving, save data is missing")
            return

        path = self.makeSavePath()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file:
            json.dump(self.updatedSaveData.toDict(), file, indent=4)
        log(f"FomodInstallerDialog: data saved into '{path}'")

    def installButtonHandlers(self) -> None:
        for button in [self.prevButton, self.nextButton]:
            if not button:
                log(f"Failed to find prev or next button in dialog")
                continue
            button.pressed.connect(self.updateSaveWithCurrentStep)
            button.clicked.connect(self.loadStepAndApplySaveState)

        if self.nextButton:
            self.nextButton.clicked.connect(self.onNextButtonClicked)

    def onNextButtonClicked(self) -> None:
        # TODO: this wouldn't work for non-English UI. 
        log(f"onNextButtonClicked '{self.nextButton.text()}'")
        if self.nextButton.text() == "Install":
            self.installClicked = True
            log(f"onNextButtonClicked installClicked = True")

    def loadSave(self) -> None:
        if self.saveData:
            return
        
        savePath = self.makeSavePath()
        data: object | None = None
        try:
            with open(savePath, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            log(f"No save for '{self.modName}', file path: '{savePath}'")
        except json.JSONDecodeError as e:
            log(f"Failed to decode JSON for file '{savePath}': '{e.msg}'")

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

        stepsStack = self.widget.findChild(QStackedWidget, "stepsStack", Qt.FindChildOption.FindChildrenRecursively)
        
        visibleStepWidget: QGroupBox | None = None
        for stepWidget in stepsStack.children():
            if isinstance(stepWidget, QGroupBox) and stepWidget.isVisibleTo(self.widget):
                visibleStepWidget = stepWidget
                break

        if not visibleStepWidget:
            log(f"Failed to find visible step widget")
            return
        
        self.currentStep.title = visibleStepWidget.title()
        for groupBox in visibleStepWidget.findChildren(QGroupBox, None, Qt.FindChildOption.FindChildrenRecursively):
            group = FomodGroup(groupBox)
            self.currentStep.groups.append(group)

            for choice in groupBox.findChildren(QCheckBox, "choice", Qt.FindChildOption.FindDirectChildrenOnly):
                group.choices.append(FomodChoice(self.plugin, choice))
            for choice in groupBox.findChildren(QRadioButton, "choice", Qt.FindChildOption.FindDirectChildrenOnly):
                group.choices.append(FomodChoice(self.plugin, choice))
    
        dumpStep(self.currentStep)

def dumpStep(step: FomodStep) -> None:
    log(f"Step title: '{step.title}'")
    for group in step.groups:
        log(f"Group: '{group.title()}'")
        for choice in group.choices:
            log(f"- Choice: '{choice.text()}, checked: {choice.isChecked()}'")

def createPlugin() -> mobase.IPlugin:
    return RememberModChoicesPlugin()
