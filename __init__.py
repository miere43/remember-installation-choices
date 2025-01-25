import os
import sys
import json
import mobase
from typing import Dict, Iterable, List, cast
from PyQt6.QtWidgets import QMainWindow, QGroupBox, QStackedWidget, QWidget, QApplication, QRadioButton, QPushButton, QCheckBox
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QWindow, QGuiApplication

currentFileFolder = os.path.dirname(os.path.realpath(__file__))

def log(s: str) -> None:
    print(s, file=sys.stderr)

class RememberModChoicesPlugin(mobase.IPlugin):
    instance: "RememberModChoicesPlugin | None" = None

    def __init__(self):
        super().__init__()

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        organizer.onUserInterfaceInitialized(lambda a: self.onUserInterfaceInitialized(a))
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

    def choiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "choice_style_sheet"))

    def disabledChoiceStyleSheet(self) -> str:
        return str(self._organizer.pluginSetting(self.name(), "disabled_choice_style_sheet"))

    def settings(self) -> List[mobase.PluginSetting]:
        return [
            mobase.PluginSetting("enabled", "enable this plugin", True),
            mobase.PluginSetting("choice_style_sheet", "Style sheet to apply to clickable choices", "background-color: rgba(0, 255, 0, 0.25)"),
            mobase.PluginSetting("disabled_choice_style_sheet", "Style sheet to apply to unclickable choices", "background-color: rgba(0, 255, 0, 0.15)"),
        ]
    
    def onUserInterfaceInitialized(self, mainWindow: QMainWindow):
        app = QApplication.instance()
        if app and isinstance(app, QGuiApplication):
            app.focusWindowChanged.connect(focusWindowChanged)

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
    
def makeSavePath(modName: str) -> str:
    return os.path.join(currentFileFolder, f"{modName}.json")

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
    def __init__(self, widget: QRadioButton | QCheckBox):
        self.widget = widget

    def text(self) -> str:
        return self.widget.text()
    
    def isChecked(self) -> bool:
        return self.widget.isChecked()
    
    def markAsPreviouslyChecked(self) -> None:
        tooltip = self.widget.toolTip()
        self.widget.setToolTip("You previously selected this choice when you installed this mod.\n\n" + tooltip)
        if plugin := RememberModChoicesPlugin.instance:
            styleSheet = plugin.choiceStyleSheet() if self.widget.isEnabled() else plugin.disabledChoiceStyleSheet()
            self.widget.setStyleSheet(f"{self.widget.__class__.__name__} {{ {styleSheet} }}")

class FomodGroup():
    def __init__(self, groupBox: QGroupBox):
        self.groupBox = groupBox
        self.choices: List[FomodChoice] = []

    def title(self) -> str:
        return self.groupBox.title()

class FomodStep():
    def __init__(self):
        self.title = ""
        self.groups: List[FomodGroup] = []

class FomodInstallerDialog():
    current: "FomodInstallerDialog | None" = None

    def onDestroyed(self) -> None:
        if FomodInstallerDialog.current != self:
            return
        
        log("FomodInstallerDialog destroyed")
        FomodInstallerDialog.current = None

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

        path = makeSavePath(self.windowTitle)
        with open(path, "w") as file:
            json.dump(self.updatedSaveData.toDict(), file, indent=4)
        log(f"FomodInstallerDialog: data saved into '{path}'")

    def __init__(self, widget: QWidget):
        self.widget = widget
        self.widget.destroyed.connect(self.onDestroyed)
        self.destroyed = False
        self.installClicked = False
        self.windowTitle = widget.windowTitle()
        self.prevButton = self.widget.findChild(QPushButton, "prevBtn", Qt.FindChildOption.FindChildrenRecursively)
        self.nextButton = self.widget.findChild(QPushButton, "nextBtn", Qt.FindChildOption.FindChildrenRecursively)
        self.saveData: FomodSave | None = None
        self.updatedSaveData: FomodSave | None = None
        self.loadSave()
        dumpChildrenWriteFile(self.widget)

    def installHandlers(self) -> None:
        for button in [self.prevButton, self.nextButton]:
            if not button:
                log(f"Failed to find prev or next button in dialog")
                continue
            button.pressed.connect(self.updateSaveWithCurrentStep)
            button.clicked.connect(self.applySaveToStep)

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
        
        data: Dict[str, object] | None
        try:
            with open(makeSavePath(self.windowTitle), "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = None
            log("The file does not exist.")
        except json.JSONDecodeError:
            data = None
            log("The file contains invalid JSON.")

        if isinstance(data, dict):
            self.saveData = FomodSave(data)
            self.updatedSaveData = FomodSave(data)

    def updateSaveWithCurrentStep(self) -> None:
        step = self.queryStep()
        dumpStep(step)

        if not self.updatedSaveData:
            self.updatedSaveData = FomodSave()

        saveStep = FomodStepSave()
        saveStep.title = step.title
        self.updatedSaveData.upsertStep(saveStep)

        for group in step.groups:
            saveGroup = FomodGroupSave()
            saveGroup.title = group.title()
            for choice in group.choices:
                saveChoice = FomodChoiceSave()
                saveChoice.text = choice.text()
                saveChoice.isChecked = choice.isChecked()
                saveGroup.choices.append(saveChoice)
            saveStep.groups.append(saveGroup)

    def applySaveToStep(self) -> None:
        if not self.saveData:
            return

        step = self.queryStep()
        dumpStep(step)
        
        saveStep = self.saveData.stepByTitle(step.title)
        if not saveStep:
            return
        
        for group in step.groups:
            saveGroup = saveStep.groupByTitle(group.title())
            if saveGroup == None:
                continue

            for choice in group.choices:
                saveChoice = saveGroup.choiceByText(choice.text())
                if saveChoice and saveChoice.isChecked:
                    choice.markAsPreviouslyChecked()

    def queryStep(self) -> FomodStep:
        step = FomodStep()
        stepsStack = self.widget.findChild(QStackedWidget, "stepsStack", Qt.FindChildOption.FindChildrenRecursively)
        
        visibleStepWidget: QGroupBox | None = None
        for stepWidget in stepsStack.children():
            if isinstance(stepWidget, QGroupBox) and stepWidget.isVisibleTo(self.widget):
                visibleStepWidget = stepWidget
                break

        if not visibleStepWidget:
            log(f"Failed to find visible step widget")
            return step
        
        step.title = visibleStepWidget.title()
        for groupBox in visibleStepWidget.findChildren(QGroupBox, None, Qt.FindChildOption.FindChildrenRecursively):
            group = FomodGroup(groupBox)
            step.groups.append(group)

            for choice in groupBox.findChildren(QCheckBox, "choice", Qt.FindChildOption.FindDirectChildrenOnly):
                group.choices.append(FomodChoice(choice))
            for choice in groupBox.findChildren(QRadioButton, "choice", Qt.FindChildOption.FindDirectChildrenOnly):
                group.choices.append(FomodChoice(choice))

        return step
    
def dumpStep(step: FomodStep) -> None:
    log(f"Step title: '{step.title}'")
    for group in step.groups:
        log(f"Group: '{group.title()}'")
        for choice in group.choices:
            log(f"- Choice: '{choice.text()}, checked: {choice.isChecked()}'")

def findInstallerDialog():
    if FomodInstallerDialog.current:
        return

    for widget in QApplication.topLevelWidgets():
        if widget.objectName() == "FomodInstallerDialog":
            FomodInstallerDialog.current = FomodInstallerDialog(widget)
            log(f"Found install window {widget}")
            break

    dialog = FomodInstallerDialog.current
    if dialog == None:
        return
    
    dialog.applySaveToStep()
    dialog.installHandlers()

def focusWindowChanged(window: QWindow | None):
    log(f"focusWindowChanged to: {window}")
    if window != None:
        findInstallerDialog()

def createPlugin() -> mobase.IPlugin:
    plugin = RememberModChoicesPlugin()
    RememberModChoicesPlugin.instance = plugin
    return plugin
