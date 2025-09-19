# Bone Flex Drivers Window for Source Filmmaker (SFM)
# Written by KiwifruitDev
# Licensed under the MIT License
#
# MIT License
# 
# Copyright (c) 2025 KiwifruitDev
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import sfm
import sfmApp
import json
import vs
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore, shiboken

try:
    sfm
except NameError:
    from sfm_runtime_builtins import *

boneFlexDriversWindow = None
boneFlexDriversVersion = "1.0.0"

class BoneFlexDriversWindow(QtGui.QWidget):
    def __init__(self):
        """
        Initialize the Bone Flex Drivers Window UI and state.
        Sets up all widgets, layouts, and connects signals.
        """
        super(BoneFlexDriversWindow, self).__init__()
        self.flexesInUse = []
        self.currentlyRefreshing = False
        self.currentShot = ""
        self.currentAnimationSet = ""
        self.currentBoneFlexDriverUniqueId = "00000000-0000-0000-0000-000000000000"

        # Layout
        self.layout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self.layout)

        # At the top, a control panel:
        # Shot dropdown, Animation Set dropdown, Refresh button
        # refresh button should be stuck to the right side, the other dropdowns should stretch to fill the space
        self.controlPanel = QtGui.QHBoxLayout()
        self.layout.addLayout(self.controlPanel)
        self.shotLabel = QtGui.QLabel("Shot:")
        self.controlPanel.addWidget(self.shotLabel)
        self.shotDropdown = QtGui.QComboBox()
        self.shotDropdown.setEnabled(False)
        self.shotDropdown.setToolTip("Select the current shot to work with")
        self.shotDropdown.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.controlPanel.addWidget(self.shotDropdown, 1)
        self.animationSetLabel = QtGui.QLabel("Animation Set:")
        self.controlPanel.addWidget(self.animationSetLabel)
        self.animationSetDropdown = QtGui.QComboBox()
        self.animationSetDropdown.setEnabled(False)
        self.animationSetDropdown.setToolTip("Select the current animation set to work with")
        self.animationSetDropdown.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        self.controlPanel.addWidget(self.animationSetDropdown, 1)
        self.refreshButton = QtGui.QPushButton("Refresh")
        self.refreshButton.setToolTip("Regenerate the bone flex driver operators and refresh the list of shots, animation sets, and bone flex drivers")
        self.controlPanel.addStretch(1)
        self.controlPanel.addWidget(self.refreshButton, 0, QtCore.Qt.AlignRight)
        self.refreshButton.clicked.connect(self.refreshBoneFlexDrivers)
        self.shotDropdown.currentIndexChanged.connect(self.shotChanged)
        self.animationSetDropdown.currentIndexChanged.connect(self.animationSetChanged)

        # Two column layout with movable splitter in-between
        # This is the main content area, so it needs to stretch to fill available space
        self.splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.splitter)
        self.topWidget = QtGui.QWidget()
        self.topWidget.setContentsMargins(0, 0, 0, 0)
        self.bottomWidget = QtGui.QWidget()
        self.bottomWidget.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.topWidget)
        self.splitter.addWidget(self.bottomWidget)
        self.splitter.setSizes([250, 250])
        self.topLayout = QtGui.QVBoxLayout()
        self.topLayout.setContentsMargins(0, 0, 4, 0)
        self.bottomLayout = QtGui.QVBoxLayout()
        self.bottomLayout.setContentsMargins(4, 0, 0, 0)
        self.topWidget.setLayout(self.topLayout)
        self.bottomWidget.setLayout(self.bottomLayout)
        self.splitter.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

        # Bone flex drivers are relationships between flexes and bones in an animation set
        # Each bone flex driver has a flex and a bone associated with an animation set
        # Bone Flex Driver -> Animation Set -> Flex & Bone

        # Top layout: Table of bone flex drivers
        self.boneFlexDriversTable = QtGui.QTableWidget()
        self.boneFlexDriversTable.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.boneFlexDriversTable.setContentsMargins(0, 0, 0, 0)
        self.boneFlexDriversTable.setEnabled(False)
        self.boneFlexDriversTable.setColumnCount(6)
        self.boneFlexDriversTable.setHorizontalHeaderLabels(["Name", "Flex", "Bone", "Value", "Active", "Unique Id"]) # active is a checkbox
        self.boneFlexDriversTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.boneFlexDriversTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.boneFlexDriversTable.itemSelectionChanged.connect(self.boneFlexDriverSelectionChanged)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.Stretch)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(4, QtGui.QHeaderView.ResizeToContents)
        self.boneFlexDriversTable.horizontalHeader().setResizeMode(5, QtGui.QHeaderView.ResizeToContents)
        # Hide the Unique Id column
        self.boneFlexDriversTable.setColumnHidden(3, True) # value is unused
        self.boneFlexDriversTable.setColumnHidden(5, True)
        self.topLayout.addWidget(self.boneFlexDriversTable)

        # Add load/save/add/remove buttons
        self.boneFlexDriversButtonsLayout = QtGui.QHBoxLayout()
        self.boneFlexDriversButtonsLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.addLayout(self.boneFlexDriversButtonsLayout)
        self.loadBoneFlexDriversButton = QtGui.QPushButton("Import")
        self.loadBoneFlexDriversButton.setEnabled(False)
        self.loadBoneFlexDriversButton.setToolTip("Load bone flex drivers from a JSON file")
        self.loadBoneFlexDriversButton.clicked.connect(self.loadBoneFlexDrivers)
        self.boneFlexDriversButtonsLayout.addWidget(self.loadBoneFlexDriversButton)
        self.saveBoneFlexDriversButton = QtGui.QPushButton("Export")
        self.saveBoneFlexDriversButton.setEnabled(False)
        self.saveBoneFlexDriversButton.setToolTip("Save bone flex drivers to a JSON file")
        self.saveBoneFlexDriversButton.clicked.connect(self.saveBoneFlexDrivers)
        self.boneFlexDriversButtonsLayout.addWidget(self.saveBoneFlexDriversButton)
        self.addBoneFlexDriverButton = QtGui.QPushButton("Add")
        self.addBoneFlexDriverButton.setEnabled(False)
        self.addBoneFlexDriverButton.setToolTip("Add a new bone flex driver")
        self.addBoneFlexDriverButton.clicked.connect(self.addBoneFlexDriver)
        self.boneFlexDriversButtonsLayout.addWidget(self.addBoneFlexDriverButton)
        self.removeBoneFlexDriverButton = QtGui.QPushButton("Remove")
        self.removeBoneFlexDriverButton.setEnabled(False)
        self.removeBoneFlexDriverButton.setToolTip("Remove the selected bone flex driver")
        self.removeBoneFlexDriverButton.clicked.connect(self.removeBoneFlexDriver)
        self.boneFlexDriversButtonsLayout.addWidget(self.removeBoneFlexDriverButton)
        self.boneFlexDriversButtonsLayout.addStretch()

        # Bottom layout: Deactivated until a bone flex driver is selected
        # Show controls for the selected bone flex driver:
        # Name (QLineEdit)
        # Active (QCheckBox)
        # Flex (QComboBox, to be populated with flexes from the animation set)
        # Min Flex Range (QDoubleSpinBox), Max Flex Range (QDoubleSpinBox)
        # Bone (QComboBox, to be populated with bones from the animation set)
        # Bone Axis (QComboBox with X, Y, Z)
        # Min Bone Range (QDoubleSpinBox), Max Bone Range (QDoubleSpinBox), Clamp (QCheckBox)
        self.boneFlexDriverDetailsGroup = QtGui.QGroupBox()
        self.boneFlexDriverDetailsGroup.setFlat(False)
        self.boneFlexDriverDetailsGroup.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.boneFlexDriverDetailsGroup.setContentsMargins(0, 0, 0, 0)
        self.boneFlexDriverDetailsGroup.setEnabled(False)
        self.bottomLayout.addWidget(self.boneFlexDriverDetailsGroup)
        self.boneFlexDriverDetailsLayout = QtGui.QFormLayout()
        self.boneFlexDriverDetailsLayout.setContentsMargins(5, 5, 5, 5)
        self.boneFlexDriverDetailsGroup.setLayout(self.boneFlexDriverDetailsLayout)
        self.boneFlexDriverNameEdit = QtGui.QLineEdit()
        self.boneFlexDriverNameEdit.setToolTip("Name of the bone flex driver")
        self.boneFlexDriverNameEdit.textChanged.connect(self.boneFlexDriverNameChanged)
        self.boneFlexDriverDetailsLayout.addRow("Name:", self.boneFlexDriverNameEdit)
        self.boneFlexDriverActiveCheckbox = QtGui.QCheckBox()
        self.boneFlexDriverActiveCheckbox.setToolTip("Whether this bone flex driver is active. When active, animation for the chosen flex will be disabled in order to be controlled by this bone flex driver.")
        self.boneFlexDriverActiveCheckbox.stateChanged.connect(self.boneFlexDriverActiveChanged)
        self.boneFlexDriverDetailsLayout.addRow("Active:", self.boneFlexDriverActiveCheckbox)
        self.flexEdit = QtGui.QComboBox()
        self.flexEdit.setToolTip("Select the flex to control")
        self.flexEdit.currentIndexChanged.connect(self.flexChanged)
        self.boneFlexDriverDetailsLayout.addRow("Flex:", self.flexEdit)
        self.minFlexRangeSpin = QtGui.QDoubleSpinBox()
        self.minFlexRangeSpin.setToolTip("Minimum flex value")
        self.minFlexRangeSpin.setRange(-1.0, 1.0)
        self.minFlexRangeSpin.setSingleStep(0.01)
        self.minFlexRangeSpin.valueChanged.connect(self.minFlexRangeChanged)
        self.boneFlexDriverDetailsLayout.addRow("Min Flex Range:", self.minFlexRangeSpin)
        self.maxFlexRangeSpin = QtGui.QDoubleSpinBox()
        self.maxFlexRangeSpin.setToolTip("Maximum flex value")
        self.maxFlexRangeSpin.setRange(-1.0, 1.0)
        self.maxFlexRangeSpin.setSingleStep(0.01)
        self.maxFlexRangeSpin.valueChanged.connect(self.maxFlexRangeChanged)
        self.boneFlexDriverDetailsLayout.addRow("Max Flex Range:", self.maxFlexRangeSpin)
        self.boneEdit = QtGui.QComboBox()
        self.boneEdit.setToolTip("Select the bone to influence the flex value.")
        self.boneEdit.currentIndexChanged.connect(self.boneChanged)
        self.boneFlexDriverDetailsLayout.addRow("Bone:", self.boneEdit)
        self.boneAxisEdit = QtGui.QComboBox()
        self.boneAxisEdit.setToolTip("Select the axis of rotation for this bone.")
        self.boneAxisEdit.addItems(["X", "Y", "Z"])
        self.boneAxisEdit.currentIndexChanged.connect(self.boneAxisChanged)
        self.boneFlexDriverDetailsLayout.addRow("Bone Axis:", self.boneAxisEdit)
        self.minBoneRangeSpin = QtGui.QDoubleSpinBox()
        self.minBoneRangeSpin.setToolTip("The minimum rotation on the chosen axis for this bone for the flex value to reach 0.")
        self.minBoneRangeSpin.setRange(-360.0, 360.0)
        self.minBoneRangeSpin.setSingleStep(1.0)
        self.minBoneRangeSpin.valueChanged.connect(self.minBoneRangeChanged)
        self.boneFlexDriverDetailsLayout.addRow("Min Bone Range:", self.minBoneRangeSpin)
        self.maxBoneRangeSpin = QtGui.QDoubleSpinBox()
        self.maxBoneRangeSpin.setToolTip("The maximum rotation on the chosen axis for this bone for the flex value to reach 1.")
        self.maxBoneRangeSpin.setRange(-360.0, 360.0)
        self.maxBoneRangeSpin.setSingleStep(1.0)
        self.maxBoneRangeSpin.valueChanged.connect(self.maxBoneRangeChanged)
        self.boneFlexDriverDetailsLayout.addRow("Max Bone Range:", self.maxBoneRangeSpin)
        self.clampCheckbox = QtGui.QCheckBox()
        self.clampCheckbox.setToolTip("Keeps the flex value within its min/max range, even if the bone value goes beyond its limits. Prevents extreme or unwanted flex movement.")
        self.clampCheckbox.stateChanged.connect(self.clampChanged)
        self.boneFlexDriverDetailsLayout.addRow("Clamp:", self.clampCheckbox)

        # Status bar
        self.statusBar = QtGui.QLabel()
        self.statusBar.setText("SFM Bone Flex Drivers by KiwifruitDev v%s" % boneFlexDriversVersion)
        self.layout.addWidget(self.statusBar)

        self.refreshBoneFlexDrivers()
    def generateOperators(self):
        """
        Regenerates SFM operators for all bone flex drivers in all shots.
        Handles undo context safely.
        """
        dm.SetUndoEnabled(False)
        shots = sfmApp.GetShots()
        for shot in shots:
            for i in range(shot.operators.count()):
                shot.operators.remove(0)
            boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
            if boneFlexDrivers is None:
                continue
            for i in range(boneFlexDrivers.count()):
                generatedOperators = getattr(boneFlexDrivers[i], "generatedOperators", None)
                if generatedOperators is None:
                    continue
                # Clear existing operators
                while generatedOperators.count() > 0:
                    generatedOperators.remove(0)
                # Create new operators based on the bone flex driver properties
                prefix = boneFlexDrivers[i].GetName() + "_" + boneFlexDrivers[i].animationSet.GetName() + "_" + boneFlexDrivers[i].boneName.GetValue() + "_" + boneFlexDrivers[i].flexName.GetValue() + "_"
                transform = vs.CreateElement("DmeConnectionOperator", (prefix + "transform").encode('utf-8'), shot.GetFileId())
                transform = generatedOperators[generatedOperators.AddToTail(transform)]
                transformInput = vs.CreateElement("DmeAttributeReference", (prefix + "transform_input").encode('utf-8'), shot.GetFileId())
                transform.SetValue("input", transformInput)
                invalidAnimationSet = False
                for j in range(boneFlexDrivers[i].animationSet.controls.count()):
                    if getattr(boneFlexDrivers[i].animationSet, "gameModel", None) is None:
                        # remove this bone flex driver, as its animation set is invalid
                        boneFlexDrivers.remove(i)
                        invalidAnimationSet = True
                        break
                    controlName = boneFlexDrivers[i].animationSet.controls[j].GetName().replace(" (disabled)", "")
                    if controlName == boneFlexDrivers[i].flexName.GetValue() or controlName == (boneFlexDrivers[i].flexName.GetValue().replace("left_", "")) or controlName == (boneFlexDrivers[i].flexName.GetValue().replace("right_", "")):
                        newValue = "flexWeight"
                        if boneFlexDrivers[i].active.GetValue():
                            boneFlexDrivers[i].animationSet.controls[j].SetName(controlName + " (disabled)")
                            newValue = "disabled"
                        else:
                            boneFlexDrivers[i].animationSet.controls[j].SetName(controlName)
                        if not hasattr(boneFlexDrivers[i].animationSet.controls[j], "channel"):
                            if boneFlexDrivers[i].flexName.GetValue().startswith("left_"):
                                boneFlexDrivers[i].animationSet.controls[j].leftvaluechannel.toAttribute.SetValue(newValue)
                            elif boneFlexDrivers[i].flexName.GetValue().startswith("right_"):
                                boneFlexDrivers[i].animationSet.controls[j].rightvaluechannel.toAttribute.SetValue(newValue)
                        else:
                            boneFlexDrivers[i].animationSet.controls[j].channel.toAttribute.SetValue(newValue)
                    if controlName == boneFlexDrivers[i].boneName.GetValue():
                        transformInput.SetValue("element", boneFlexDrivers[i].animationSet.controls[j].orientationChannel.toElement)
                        break
                if invalidAnimationSet:
                    continue # skip the rest of this loop iteration
                transformInput.attribute.SetValue("orientation")
                transformOutput = vs.CreateElement("DmeAttributeReference", (prefix + "transform_output").encode('utf-8'), shot.GetFileId())
                transform.outputs.AddToTail(transformOutput)
                unpack = vs.CreateElement("DmeUnpackQuaternionOperator", (prefix + "unpack").encode('utf-8'), shot.GetFileId())
                unpack = generatedOperators[generatedOperators.AddToTail(unpack)]
                transformOutput.SetValue("element", unpack)
                transformOutput.attribute.SetValue("quaternion")
                wName = prefix + "w"
                w = vs.CreateElement("DmeConnectionOperator", (wName).encode('utf-8'), shot.GetFileId())
                w = generatedOperators[generatedOperators.AddToTail(w)]
                wInput = vs.CreateElement("DmeAttributeReference", (prefix + "w_input").encode('utf-8'), shot.GetFileId())
                w.SetValue("input", wInput)
                wInput.SetValue("element", unpack)
                wInput.attribute.SetValue("w")
                wOutput = vs.CreateElement("DmeAttributeReference", (prefix + "w_output").encode('utf-8'), shot.GetFileId())
                w.outputs.AddToTail(wOutput)
                eval = vs.CreateElement("DmeExpressionOperator", (prefix + "eval").encode('utf-8'), shot.GetFileId())
                wOutput.SetValue("element", eval)
                eval = generatedOperators[generatedOperators.AddToTail(eval)]
                isX = "rtod(atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y)))"
                isY = "rtod(asin(2*(w*y - z*x)))"
                isZ = "rtod(atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))"
                axisExpr = {"X": isX, "Y": isY, "Z": isZ}.get(boneFlexDrivers[i].boneAxis.GetValue().upper(), isX)
                axisExpr = "ramp(%s, %f, %f)" % (axisExpr, boneFlexDrivers[i].minBoneRange.GetValue(), boneFlexDrivers[i].maxBoneRange.GetValue())
                if boneFlexDrivers[i].clamp.GetValue():
                    axisExpr = "clamp(%s, 0, 1)" % axisExpr
                # Map flex range from minFlexRange to maxFlexRange
                axisExpr = "lerp(%s, %f, %f)" % (axisExpr, boneFlexDrivers[i].minFlexRange.GetValue(), boneFlexDrivers[i].maxFlexRange.GetValue())
                eval.expr.SetValue(axisExpr)
                eval.AddAttribute("w", vs.AT_FLOAT)
                eval.AddAttribute("x", vs.AT_FLOAT)
                eval.AddAttribute("y", vs.AT_FLOAT)
                eval.AddAttribute("z", vs.AT_FLOAT)
                wOutput.attribute.SetValue("w")
                x = vs.CreateElement("DmeConnectionOperator", (prefix + "x").encode('utf-8'), shot.GetFileId())
                x = generatedOperators[generatedOperators.AddToTail(x)]
                xInput = vs.CreateElement("DmeAttributeReference", (prefix + "x_input").encode('utf-8'), shot.GetFileId())
                x.SetValue("input", xInput)
                xInput.SetValue("element", unpack)
                xInput.attribute.SetValue("x")
                xOutput = vs.CreateElement("DmeAttributeReference", (prefix + "x_output").encode('utf-8'), shot.GetFileId())
                x.outputs.AddToTail(xOutput)
                xOutput.SetValue("element", eval)
                xOutput.attribute.SetValue("x")
                y = vs.CreateElement("DmeConnectionOperator", (prefix + "y").encode('utf-8'), shot.GetFileId())
                y = generatedOperators[generatedOperators.AddToTail(y)]
                yInput = vs.CreateElement("DmeAttributeReference", (prefix + "y_input").encode('utf-8'), shot.GetFileId())
                y.SetValue("input", yInput)
                yInput.SetValue("element", unpack)
                yInput.attribute.SetValue("y")
                yOutput = vs.CreateElement("DmeAttributeReference", (prefix + "y_output").encode('utf-8'), shot.GetFileId())
                y.outputs.AddToTail(yOutput)
                yOutput.SetValue("element", eval)
                yOutput.attribute.SetValue("y")
                z = vs.CreateElement("DmeConnectionOperator", (prefix + "z").encode('utf-8'), shot.GetFileId())
                z = generatedOperators[generatedOperators.AddToTail(z)]
                zInput = vs.CreateElement("DmeAttributeReference", (prefix + "z_input").encode('utf-8'), shot.GetFileId())
                z.SetValue("input", zInput)
                zInput.SetValue("element", unpack)
                zInput.attribute.SetValue("z")
                zOutput = vs.CreateElement("DmeAttributeReference", (prefix + "z_output").encode('utf-8'), shot.GetFileId())
                z.outputs.AddToTail(zOutput)
                zOutput.SetValue("element", eval)
                zOutput.attribute.SetValue("z")
                generatedOperators.AddToTail(z)
                result = vs.CreateElement("DmeConnectionOperator", (prefix + "result").encode('utf-8'), shot.GetFileId())
                result = generatedOperators[generatedOperators.AddToTail(result)]
                resultInput = vs.CreateElement("DmeAttributeReference", (prefix + "result_input").encode('utf-8'), shot.GetFileId())
                result.SetValue("input", resultInput)
                resultInput.SetValue("element", eval)
                resultInput.attribute.SetValue("result")
                resultOutput = vs.CreateElement("DmeAttributeReference", (prefix + "result_output").encode('utf-8'), shot.GetFileId())
                result.outputs.AddToTail(resultOutput)
                for j in range(boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers.count()):
                    if boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers[j].GetName() == boneFlexDrivers[i].flexName.GetValue():
                        resultOutput.SetValue("element", boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers[j])
                        break
                resultOutput.attribute.SetValue("flexWeight")
                if boneFlexDrivers[i].active.GetValue():
                    for j in range(generatedOperators.count()):
                        shot.operators.AddToTail(generatedOperators[j])
        dm.SetUndoEnabled(True)

    def refreshBoneFlexDrivers(self):
        if self.currentlyRefreshing == True:
            return
        self.currentlyRefreshing = True
        self.flexesInUse = []
        hasDocument = sfmApp.HasDocument()
        self.shotDropdown.clear()
        self.animationSetDropdown.clear()
        self.boneFlexDriversTable.setRowCount(0)
        self.shotDropdown.setEnabled(hasDocument)
        self.animationSetDropdown.setEnabled(False)
        self.boneFlexDriversTable.setEnabled(False)
        # Populate shot dropdown
        if hasDocument:
            shots = sfmApp.GetShots()
            for shot in shots:
                self.shotDropdown.addItem(shot.GetName())
                if shot.GetName() == self.currentShot:
                    self.shotDropdown.setCurrentIndex(self.shotDropdown.count() - 1)
        self.generateOperators()
        self.currentlyRefreshing = False
    def shotChanged(self, index):
        self.animationSetDropdown.clear()
        if index < 0:
            self.animationSetDropdown.setEnabled(False)
            return
        self.animationSetDropdown.setEnabled(True)
        # populate animation set dropdown based on selected shot
        shotName = self.shotDropdown.itemText(index)
        self.currentShot = shotName
        shots = sfmApp.GetShots()
        currentAnimationSet = self.currentAnimationSet
        for shot in shots:
            if shot.GetName() == shotName:
                animationSets = shot.animationSets
                for i in range(animationSets.count()):
                    # must have gameModel attribute
                    if getattr(animationSets[i], "gameModel", None) is None:
                        continue
                    self.animationSetDropdown.addItem(animationSets[i].GetName())
                    self.currentAnimationSet = currentAnimationSet
                    if animationSets[i].GetName() == currentAnimationSet:
                        self.animationSetDropdown.setCurrentIndex(self.animationSetDropdown.count() - 1)
                break
    def animationSetChanged(self, index):
        self.boneFlexDriversTable.setRowCount(0)
        self.boneFlexDriversTable.setEnabled(False)
        self.loadBoneFlexDriversButton.setEnabled(False)
        self.saveBoneFlexDriversButton.setEnabled(False)
        self.addBoneFlexDriverButton.setEnabled(False)
        self.removeBoneFlexDriverButton.setEnabled(False)
        self.boneFlexDriverDetailsGroup.setEnabled(False)
        if index < 0:
            return
        # shot.boneFlexDrivers is an array of bone flex drivers, each have an animationSet element with a name attribute
        # get all of the shot's boneFlexDrivers and filter them by the selected animation set
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.itemText(index)
        self.currentAnimationSet = animSetName
        shots = sfmApp.GetShots()
        addedBoneFlexDriver = False
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                # if boneFlexDrivers is None, create it
                if boneFlexDrivers is None:
                    boneFlexDrivers = shot.AddAttribute("boneFlexDrivers", vs.AT_ELEMENT_ARRAY)
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].animationSet.GetName() == animSetName:
                        # Get bone flex driver properties
                        active = boneFlexDrivers[i].active.GetValue()
                        flexName = boneFlexDrivers[i].flexName.GetValue()
                        boneName = boneFlexDrivers[i].boneName.GetValue()
                        self.flexesInUse.append(flexName)
                        # Populate the table with this bone flex driver
                        rowPosition = self.boneFlexDriversTable.rowCount()
                        self.boneFlexDriversTable.insertRow(rowPosition)
                        nameItem = QtGui.QTableWidgetItem(boneFlexDrivers[i].name.GetValue())
                        nameItem.setFlags(nameItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.boneFlexDriversTable.setItem(rowPosition, 0, nameItem)
                        flexItem = QtGui.QTableWidgetItem(flexName)
                        flexItem.setFlags(flexItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.boneFlexDriversTable.setItem(rowPosition, 1, flexItem)
                        boneItem = QtGui.QTableWidgetItem(boneName)
                        boneItem.setFlags(boneItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.boneFlexDriversTable.setItem(rowPosition, 2, boneItem)
                        valueItem = QtGui.QTableWidgetItem("0.0")
                        valueItem.setFlags(valueItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.boneFlexDriversTable.setItem(rowPosition, 3, valueItem)
                        uniqueId = boneFlexDrivers[i].GetId().__str__()
                        activeCheckBox = QtGui.QCheckBox()
                        activeCheckBox.setChecked(active)
                        activeCheckBox.toggled.connect(lambda checked, uniqueId=uniqueId: self.onBoneFlexDriverActiveChanged(checked, uniqueId))
                        self.boneFlexDriversTable.setCellWidget(rowPosition, 4, activeCheckBox)
                        uniqueIdItem = QtGui.QTableWidgetItem(uniqueId)
                        uniqueIdItem.setFlags(uniqueIdItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.boneFlexDriversTable.setItem(rowPosition, 5, uniqueIdItem)
                        addedBoneFlexDriver = True
                        if self.currentBoneFlexDriverUniqueId == uniqueId:
                            self.boneFlexDriversTable.selectRow(rowPosition)
                break
        self.boneFlexDriversTable.setEnabled(True)
        self.loadBoneFlexDriversButton.setEnabled(True)
        self.addBoneFlexDriverButton.setEnabled(True)
        if addedBoneFlexDriver:
            self.saveBoneFlexDriversButton.setEnabled(True)
        dm.SetUndoEnabled(True)
    def boneFlexDriverSelectionChanged(self):
        # get selection
        selectedItems = self.boneFlexDriversTable.selectedItems()
        if not selectedItems:
            self.boneFlexDriverDetailsGroup.setEnabled(False)
            self.removeBoneFlexDriverButton.setEnabled(False)
            return
        self.boneFlexDriverDetailsGroup.setEnabled(True)
        self.removeBoneFlexDriverButton.setEnabled(True)
        selectedRow = selectedItems[0].row()
        uniqueIdItem = self.boneFlexDriversTable.item(selectedRow, 5)
        self.currentBoneFlexDriverUniqueId = uniqueIdItem.text()
        # Populate the details panel with the selected bone flex driver's properties
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        # Found the bone flex driver, populate details
                        self.boneFlexDriverNameEdit.setText(boneFlexDrivers[i].name.GetValue())
                        self.boneFlexDriverActiveCheckbox.setChecked(boneFlexDrivers[i].active.GetValue())
                        # Populate flex dropdown
                        matchingFlex = boneFlexDrivers[i].flexName.GetValue()
                        self.flexEdit.clear()
                        flexes = []
                        storeFlexesInUse = self.flexesInUse[:]
                        self.flexesInUse =  []
                        if boneFlexDrivers[i].animationSet:
                            for j in range(boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers.count()):
                                if boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers[j] is None:
                                    continue
                                flexName = boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers[j].GetName()
                                self.flexEdit.addItem(flexName)
                                flexes.append(flexName.replace("left_", "").replace("right_", ""))
                                if boneFlexDrivers[i].animationSet.gameModel.globalFlexControllers[j].GetName() == matchingFlex:
                                    self.flexEdit.setCurrentIndex(self.flexEdit.count() - 1)
                        self.flexesInUse = storeFlexesInUse + [matchingFlex] # workaround to prevent conflict errors when setting up properties
                        self.minFlexRangeSpin.setValue(boneFlexDrivers[i].minFlexRange.GetValue() if hasattr(boneFlexDrivers[i], "minFlexRange") else 0.0)
                        self.maxFlexRangeSpin.setValue(boneFlexDrivers[i].maxFlexRange.GetValue() if hasattr(boneFlexDrivers[i], "maxFlexRange") else 1.0)
                        # Populate bone dropdown
                        matchingBone = boneFlexDrivers[i].boneName.GetValue()
                        self.boneEdit.clear()
                        if boneFlexDrivers[i].animationSet:
                            for j in range(boneFlexDrivers[i].animationSet.controls.count()):
                                if boneFlexDrivers[i].animationSet.controls[j] is None:
                                    continue
                                controlName = boneFlexDrivers[i].animationSet.controls[j].GetName().replace(" (disabled)", "")
                                if " - " in controlName:
                                    # a rig script created this control, skip it
                                    continue
                                # the name cannot be the same as a flex
                                if controlName not in flexes:
                                    self.boneEdit.addItem(controlName)
                                    if controlName == matchingBone:
                                        self.boneEdit.setCurrentIndex(self.boneEdit.count() - 1)
                        axis = boneFlexDrivers[i].boneAxis.GetValue().upper() if hasattr(boneFlexDrivers[i], "boneAxis") else "X"
                        axisIndex = {"X": 0, "Y": 1, "Z": 2}.get(axis, 0)
                        self.boneAxisEdit.setCurrentIndex(axisIndex)
                        self.minBoneRangeSpin.setValue(boneFlexDrivers[i].minBoneRange.GetValue() if hasattr(boneFlexDrivers[i], "minBoneRange") else 0.0)
                        self.maxBoneRangeSpin.setValue(boneFlexDrivers[i].maxBoneRange.GetValue() if hasattr(boneFlexDrivers[i], "maxBoneRange") else 90.0)
                        self.clampCheckbox.setChecked(boneFlexDrivers[i].clamp.GetValue() if hasattr(boneFlexDrivers[i], "clamp") else True)
                        break
    def loadBoneFlexDrivers(self):
        """
        Loads bone flex drivers from a JSON file and adds them to the current animation set.
        Provides error handling and validation.
        """
        # Load bone flex drivers from a JSON file and add them to the current animation set
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        options = QtGui.QFileDialog.Options()
        options |= QtGui.QFileDialog.DontUseNativeDialog
        fileName, _ = QtGui.QFileDialog.getOpenFileName(self, "Load Bone Flex Drivers", "", "JSON Files (*.json);;All Files (*)", options=options)
        if fileName:
            dm.SetUndoEnabled(False)
            try:
                with open(fileName, 'r') as f:
                    boneFlexDriversToLoad = json.load(f)
                if not isinstance(boneFlexDriversToLoad, list):
                    QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Invalid bone flex drivers file format. Expected a list of bone flex drivers.")
                    dm.SetUndoEnabled(True)
                    return
                shots = sfmApp.GetShots()
                for shot in shots:
                    if shot.GetName() == shotName:
                        boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                        if boneFlexDrivers is None:
                            boneFlexDrivers = shot.AddAttribute("boneFlexDrivers", vs.AT_ELEMENT_ARRAY)
                        for boneFlexDriverData in boneFlexDriversToLoad:
                            if not isinstance(boneFlexDriverData, dict):
                                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Malformed bone flex driver entry: %s" % str(boneFlexDriverData))
                                continue
                            name = boneFlexDriverData.get("name", "").strip()
                            flexName = boneFlexDriverData.get("flexName", "").strip()
                            boneName = boneFlexDriverData.get("boneName", "").strip()
                            if not name or not flexName or not boneName:
                                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Missing required fields in bone flex driver: %s" % str(boneFlexDriverData))
                                continue
                            if flexName in self.flexesInUse:
                                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Could not import Bone Flex Driver '%s'\nFlex '%s' is already in use by another bone flex driver" % (name, flexName))
                                continue
                            newBoneFlexDriver = vs.CreateElement("DmElement", name.encode('utf-8'), shot.GetFileId())
                            newBoneFlexDriver = boneFlexDrivers[boneFlexDrivers.AddToTail(newBoneFlexDriver)]
                            newBoneFlexDriver.AddAttribute("active", vs.AT_BOOL).SetValue(boneFlexDriverData.get("active", True))
                            newBoneFlexDriver.AddAttribute("flexName", vs.AT_STRING).SetValue(flexName.encode('utf-8'))
                            newBoneFlexDriver.AddAttribute("boneName", vs.AT_STRING).SetValue(boneName.encode('utf-8'))
                            newBoneFlexDriver.AddAttribute("minFlexRange", vs.AT_FLOAT).SetValue(boneFlexDriverData.get("minFlexRange", 0.0))
                            newBoneFlexDriver.AddAttribute("maxFlexRange", vs.AT_FLOAT).SetValue(boneFlexDriverData.get("maxFlexRange", 1.0))
                            newBoneFlexDriver.AddAttribute("boneAxis", vs.AT_STRING).SetValue(boneFlexDriverData.get("boneAxis", "X").upper().encode('utf-8'))
                            newBoneFlexDriver.AddAttribute("minBoneRange", vs.AT_FLOAT).SetValue(boneFlexDriverData.get("minBoneRange", 0.0))
                            newBoneFlexDriver.AddAttribute("maxBoneRange", vs.AT_FLOAT).SetValue(boneFlexDriverData.get("maxBoneRange", 90.0))
                            newBoneFlexDriver.AddAttribute("clamp", vs.AT_BOOL).SetValue(boneFlexDriverData.get("clamp", True))
                            newBoneFlexDriver.AddAttribute("generatedOperators", vs.AT_ELEMENT_ARRAY)
                            animationSetAttribute = newBoneFlexDriver.AddAttribute("animationSet", vs.AT_ELEMENT)
                            for i in range(shot.animationSets.count()):
                                if shot.animationSets[i].GetName() == animSetName:
                                    animationSetAttribute.SetValue(shot.animationSets[i])
                                    break
                            self.flexesInUse.append(flexName)
            except Exception as e:
                QtGui.QMessageBox.critical(self, "Bone Flex Drivers: Error", "Failed to load bone flex drivers: %s" % str(e))
            dm.SetUndoEnabled(True)
            self.refreshBoneFlexDrivers()
            self.animationSetChanged(self.animationSetDropdown.currentIndex())
    def saveBoneFlexDrivers(self):
        # Save the current animation set's bone flex drivers to a JSON file
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "No bone flex drivers to save")
                    dm.SetUndoEnabled(True)
                    return
                boneFlexDriversToSave = []
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].animationSet.GetName() == animSetName:
                        boneFlexDriverData = {
                            "name": boneFlexDrivers[i].name.GetValue(),
                            "active": boneFlexDrivers[i].active.GetValue(),
                            "flexName": boneFlexDrivers[i].flexName.GetValue(),
                            "boneName": boneFlexDrivers[i].boneName.GetValue(),
                            "minFlexRange": boneFlexDrivers[i].minFlexRange.GetValue() if hasattr(boneFlexDrivers[i], "minFlexRange") else 0.0,
                            "maxFlexRange": boneFlexDrivers[i].maxFlexRange.GetValue() if hasattr(boneFlexDrivers[i], "maxFlexRange") else 1.0,
                            "boneAxis": boneFlexDrivers[i].boneAxis.GetValue() if hasattr(boneFlexDrivers[i], "boneAxis") else "X",
                            "minBoneRange": boneFlexDrivers[i].minBoneRange.GetValue() if hasattr(boneFlexDrivers[i], "minBoneRange") else 0.0,
                            "maxBoneRange": boneFlexDrivers[i].maxBoneRange.GetValue() if hasattr(boneFlexDrivers[i], "maxBoneRange") else 90.0,
                            "clamp": boneFlexDrivers[i].clamp.GetValue() if hasattr(boneFlexDrivers[i], "clamp") else True,
                        }
                        boneFlexDriversToSave.append(boneFlexDriverData)
                if not boneFlexDriversToSave:
                    QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "No bone flex drivers to save for the selected animation set")
                    dm.SetUndoEnabled(True)
                    return
                options = QtGui.QFileDialog.Options()
                options |= QtGui.QFileDialog.DontUseNativeDialog
                fileName, _ = QtGui.QFileDialog.getSaveFileName(self, "Save Bone Flex Drivers", "", "JSON Files (*.json);;All Files (*)", options=options)
                if fileName:
                    try:
                        # Append .json extension if not present
                        if not fileName.lower().endswith('.json'):
                            fileName += '.json'
                        with open(fileName, 'w') as f:
                            json.dump(boneFlexDriversToSave, f, indent=4)
                        QtGui.QMessageBox.information(self, "Bone Flex Drivers: Success", "Bone flex drivers saved successfully")
                    except Exception as e:
                        QtGui.QMessageBox.critical(self, "Bone Flex Drivers: Error", "Failed to save bone flex drivers: %s" % str(e))
        dm.SetUndoEnabled(True)
    def addBoneFlexDriver(self):
        # Dialog box to set name and select flex/bone
        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle("Add Bone Flex Driver")
        dialogLayout = QtGui.QFormLayout()
        dialog.setLayout(dialogLayout)
        nameEdit = QtGui.QLineEdit()
        nameEdit.setText("boneFlexDriver%d" % (self.boneFlexDriversTable.rowCount() + 1))
        dialogLayout.addRow("Name:", nameEdit)
        flexEdit = QtGui.QComboBox()
        dialogLayout.addRow("Flex:", flexEdit)
        boneEdit = QtGui.QComboBox()
        dialogLayout.addRow("Bone:", boneEdit)
        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        dialogLayout.addRow(buttonBox)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        # Populate flex and bone dropdowns based on current animation set
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                for i in range(shot.animationSets.count()):
                    if shot.animationSets[i].GetName() == animSetName:
                        flexes = []
                        for j in range(shot.animationSets[i].gameModel.globalFlexControllers.count()):
                            if shot.animationSets[i].gameModel.globalFlexControllers[j] is None:
                                continue
                            flexName = shot.animationSets[i].gameModel.globalFlexControllers[j].GetName()
                            flexEdit.addItem(flexName)
                            flexes.append(flexName)
                            flexes.append(flexName.replace("left_", "").replace("right_", "").replace("multi_", ""))
                        for j in range(shot.animationSets[i].controls.count()):
                            if shot.animationSets[i].controls[j] is None:
                                continue
                            controlName = shot.animationSets[i].controls[j].GetName().replace(" (disabled)", "")
                            if " - " in controlName:
                                # a rig script created this control, skip it
                                continue
                            # the name cannot be the same as a flex
                            if controlName not in flexes:
                                boneEdit.addItem(controlName)
                        break
                break
        if dialog.exec_() == QtGui.QDialog.Accepted:
            name = nameEdit.text().strip()
            flexName = flexEdit.currentText()
            boneName = boneEdit.currentText()
            if not name:
                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Name cannot be empty")
                return
            if not flexName:
                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Flex must be selected")
                return
            if flexName in self.flexesInUse:
                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Flex '%s' is already in use by another bone flex driver" % flexName)
                return
            if not boneName:
                QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Bone must be selected")
                return
            # Add the bone flex driver to the shot's boneFlexDrivers array
            dm.SetUndoEnabled(False)
            for shot in shots:
                if shot.GetName() == shotName:
                    boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                    if boneFlexDrivers is None:
                        boneFlexDrivers = shot.AddAttribute("boneFlexDrivers", vs.AT_ELEMENT_ARRAY)
                    newBoneFlexDriver = vs.CreateElement("DmElement", name.encode('utf-8'), shot.GetFileId())
                    newBoneFlexDriver.AddAttribute("active", vs.AT_BOOL).SetValue(True)
                    newBoneFlexDriver.AddAttribute("flexName", vs.AT_STRING).SetValue(flexName.encode('utf-8'))
                    newBoneFlexDriver.AddAttribute("boneName", vs.AT_STRING).SetValue(boneName.encode('utf-8'))
                    newBoneFlexDriver.AddAttribute("minFlexRange", vs.AT_FLOAT).SetValue(0.0)
                    newBoneFlexDriver.AddAttribute("maxFlexRange", vs.AT_FLOAT).SetValue(1.0)
                    newBoneFlexDriver.AddAttribute("boneAxis", vs.AT_STRING).SetValue("X".encode('utf-8'))
                    newBoneFlexDriver.AddAttribute("minBoneRange", vs.AT_FLOAT).SetValue(0.0)
                    newBoneFlexDriver.AddAttribute("maxBoneRange", vs.AT_FLOAT).SetValue(90.0)
                    newBoneFlexDriver.AddAttribute("clamp", vs.AT_BOOL).SetValue(True)
                    newBoneFlexDriver.AddAttribute("generatedOperators", vs.AT_ELEMENT_ARRAY)
                    for i in range(shot.animationSets.count()):
                        if shot.animationSets[i].GetName() == animSetName:
                            newBoneFlexDriver.AddAttribute("animationSet", vs.AT_ELEMENT).SetValue(shot.animationSets[i])
                            break
                    boneFlexDrivers.AddToTail(newBoneFlexDriver)
            self.refreshBoneFlexDrivers()
            dm.SetUndoEnabled(True)
    def removeBoneFlexDriver(self):
        if not self.currentBoneFlexDriverUniqueId:
            return
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        # Found the bone flex driver, remove it
                        for j in range(boneFlexDrivers[i].animationSet.controls.count()):
                            if boneFlexDrivers[i].animationSet.controls[j] is None:
                                continue
                            controlName = boneFlexDrivers[i].animationSet.controls[j].GetName().replace(" (disabled)", "")
                            if controlName == boneFlexDrivers[i].flexName.GetValue() or controlName == boneFlexDrivers[i].flexName.GetValue().replace("left_", "").replace("right_", ""):
                                boneFlexDrivers[i].animationSet.controls[j].SetName(controlName)
                                # if channel attribute doesn't exist, find "left"/"right" + "valuechannel"
                                if not hasattr(boneFlexDrivers[i].animationSet.controls[j], "channel"):
                                    if boneFlexDrivers[i].flexName.GetValue().startswith("left_"):
                                        boneFlexDrivers[i].animationSet.controls[j].leftvaluechannel.toAttribute.SetValue("flexWeight")
                                    elif boneFlexDrivers[i].flexName.GetValue().startswith("right_"):
                                        boneFlexDrivers[i].animationSet.controls[j].rightvaluechannel.toAttribute.SetValue("flexWeight")
                                else:
                                    boneFlexDrivers[i].animationSet.controls[j].channel.toAttribute.SetValue("flexWeight")
                                break
                        boneFlexDrivers.remove(i)
                        break
                break
        dm.SetUndoEnabled(True)
        self.currentBoneFlexDriverUniqueId = "00000000-0000-0000-0000-000000000000"
        self.refreshBoneFlexDrivers()
    def boneFlexDriverNameChanged(self, text):
        # Update the name in the table and the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if boneFlexDrivers[i].name.GetValue() == text:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its name
                        boneFlexDrivers[i].SetName(text.encode('utf-8'))
                        # Update the name in the table
                        for row in range(self.boneFlexDriversTable.rowCount()):
                            uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                                nameItem = self.boneFlexDriversTable.item(row, 0)
                                nameItem.setText(text)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
    def boneFlexDriverActiveChanged(self, state):
        # Update the active checkbox in the table and the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        dm.SetUndoEnabled(False)
                        boneFlexDrivers[i].active.SetValue(state)
                        dm.SetUndoEnabled(True)
                        # Update the checkbox in the table
                        for row in range(self.boneFlexDriversTable.rowCount()):
                            uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                                activeCheckBox = self.boneFlexDriversTable.cellWidget(row, 4)
                                activeCheckBox.setChecked(state)
                        break
        self.generateOperators()
    def flexChanged(self, index):
        if index < 0:
            return
        # Update the flex name in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        flexName = self.flexEdit.itemText(index)
        if flexName in self.flexesInUse and flexName != self.boneFlexDriversTable.item(self.boneFlexDriversTable.currentRow(), 1).text():
            QtGui.QMessageBox.warning(self, "Bone Flex Drivers: Error", "Flex '%s' is already in use by another bone flex driver" % flexName)
            # revert to previous selection
            for row in range(self.boneFlexDriversTable.rowCount()):
                uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                    flexItem = self.boneFlexDriversTable.item(row, 1)
                    currentFlexName = flexItem.text()
                    for i in range(self.flexEdit.count()):
                        if self.flexEdit.itemText(i) == currentFlexName:
                            self.flexEdit.setCurrentIndex(i)
                            break
                    break
            return
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if boneFlexDrivers[i].flexName.GetValue() == flexName:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its flex name
                        # Reset channel attribute on the flex control if it exists
                        for j in range(boneFlexDrivers[i].animationSet.controls.count()):
                            if boneFlexDrivers[i].animationSet.controls[j] is None:
                                continue
                            controlName = boneFlexDrivers[i].animationSet.controls[j].GetName().replace(" (disabled)", "")
                            if controlName == boneFlexDrivers[i].flexName.GetValue() or controlName == boneFlexDrivers[i].flexName.GetValue().replace("left_", "").replace("right_", ""):
                                boneFlexDrivers[i].animationSet.controls[j].SetName(controlName)
                                # if channel attribute doesn't exist, find "left"/"right" + "valuechannel"
                                if not hasattr(boneFlexDrivers[i].animationSet.controls[j], "channel"):
                                    if boneFlexDrivers[i].flexName.GetValue().startswith("left_"):
                                        boneFlexDrivers[i].animationSet.controls[j].leftvaluechannel.toAttribute.SetValue("flexWeight")
                                    elif boneFlexDrivers[i].flexName.GetValue().startswith("right_"):
                                        boneFlexDrivers[i].animationSet.controls[j].rightvaluechannel.toAttribute.SetValue("flexWeight")
                                else:
                                    boneFlexDrivers[i].animationSet.controls[j].channel.toAttribute.SetValue("flexWeight")
                                break
                        boneFlexDrivers[i].flexName.SetValue(flexName.encode('utf-8'))
                        # Update the flex name in the table
                        for row in range(self.boneFlexDriversTable.rowCount()):
                            uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                                flexItem = self.boneFlexDriversTable.item(row, 1)
                                flexItem.setText(flexName)
                        break
                break
        dm.SetUndoEnabled(True)
        self.refreshBoneFlexDrivers()
    def minFlexRangeChanged(self, value):
        # Update the min flex range in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(boneFlexDrivers[i], "minFlexRange") and boneFlexDrivers[i].minFlexRange.GetValue() == value:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its min flex range
                        if not hasattr(boneFlexDrivers[i], "minFlexRange"):
                            boneFlexDrivers[i].AddAttribute("minFlexRange", vs.AT_FLOAT)
                        boneFlexDrivers[i].minFlexRange.SetValue(value)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def maxFlexRangeChanged(self, value):
        # Update the max flex range in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(boneFlexDrivers[i], "maxFlexRange") and boneFlexDrivers[i].maxFlexRange.GetValue() == value:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its max flex range
                        if not hasattr(boneFlexDrivers[i], "maxFlexRange"):
                            boneFlexDrivers[i].AddAttribute("maxFlexRange", vs.AT_FLOAT)
                        boneFlexDrivers[i].maxFlexRange.SetValue(value)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def boneChanged(self, index):
        if index < 0:
            return
        # Update the bone name in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        boneName = self.boneEdit.itemText(index)
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if boneFlexDrivers[i].boneName.GetValue() == boneName:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its bone name
                        boneFlexDrivers[i].boneName.SetValue(boneName.encode('utf-8'))
                        # Update the bone name in the table
                        for row in range(self.boneFlexDriversTable.rowCount()):
                            uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                                boneItem = self.boneFlexDriversTable.item(row, 2)
                                boneItem.setText(boneName)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def boneAxisChanged(self, index):
        if index < 0:
            return
        # Update the bone axis in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        boneAxis = self.boneAxisEdit.itemText(index)
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if boneFlexDrivers[i].boneAxis.GetValue() == boneAxis:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its bone axis
                        boneFlexDrivers[i].boneAxis.SetValue(boneAxis.encode('utf-8'))
                        # Update the bone axis in the table
                        for row in range(self.boneFlexDriversTable.rowCount()):
                            uniqueIdItem = self.boneFlexDriversTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentBoneFlexDriverUniqueId:
                                boneAxisItem = self.boneFlexDriversTable.item(row, 3)
                                boneAxisItem.setText(boneAxis)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def minBoneRangeChanged(self, value):
        # Update the min bone range in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(boneFlexDrivers[i], "minBoneRange") and boneFlexDrivers[i].minBoneRange.GetValue() == value:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its min bone range
                        if not hasattr(boneFlexDrivers[i], "minBoneRange"):
                            boneFlexDrivers[i].AddAttribute("minBoneRange", vs.AT_FLOAT)
                        boneFlexDrivers[i].minBoneRange.SetValue(value)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def maxBoneRangeChanged(self, value):
        # Update the max bone range in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(boneFlexDrivers[i], "maxBoneRange") and boneFlexDrivers[i].maxBoneRange.GetValue() == value:
                            dm.SetUndoEnabled(True)
                            return # no change
                        # Found the bone flex driver, update its max bone range
                        if not hasattr(boneFlexDrivers[i], "maxBoneRange"):
                            boneFlexDrivers[i].AddAttribute("maxBoneRange", vs.AT_FLOAT)
                        boneFlexDrivers[i].maxBoneRange.SetValue(value)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def clampChanged(self, state):
        # Update the clamp checkbox in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == self.currentBoneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        boneFlexDrivers[i].clamp.SetValue(state)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshBoneFlexDrivers()
    def onBoneFlexDriverActiveChanged(self, checked, boneFlexDriverUniqueId):
        if self.currentBoneFlexDriverUniqueId == boneFlexDriverUniqueId:
            # Update the checkbox in the details panel if it matches the current bone flex driver
            self.boneFlexDriverActiveCheckbox.setChecked(checked)
            return # already handled in boneFlexDriverActiveChanged
        # Update the active state in the bone flex driver object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        dm.SetUndoEnabled(False)
        for shot in shots:
            if shot.GetName() == shotName:
                boneFlexDrivers = getattr(shot, "boneFlexDrivers", None)
                if boneFlexDrivers is None:
                    break
                for i in range(boneFlexDrivers.count()):
                    if boneFlexDrivers[i].GetId().__str__() == boneFlexDriverUniqueId and boneFlexDrivers[i].animationSet.name.GetValue() == animSetName:
                        boneFlexDrivers[i].active.SetValue(checked)
                        break
                break
        dm.SetUndoEnabled(True)
        self.generateOperators()

def createBoneFlexDriversWindow():
    try:
        boneFlexDriversWindow = BoneFlexDriversWindow()
        pointer = shiboken.getCppPointer(boneFlexDriversWindow)
        sfmApp.RegisterTabWindow("BoneFlexDriversWindow", "Bone Flex Drivers", pointer[0])
        globals()["global_boneFlexDriversWindow"] = boneFlexDriversWindow
    except Exception as e:
        import traceback
        traceback.print_exc()        
        msgBox = QtGui.QMessageBox()
        msgBox.setText("Error: %s" % e)
        msgBox.exec_()

try:
    # Create window if it doesn't exist
    firstWindow = globals().get("global_boneFlexDriversWindow")
    if firstWindow is None:
        createBoneFlexDriversWindow()
    else:
        dialog = QtGui.QMessageBox.warning(None, "Bone Flex Drivers: Error", "The Bone Flex Drivers window is already open.\nIf you are a developer, click Yes to forcibly open a new instance.\nOtherwise, click No to close this message.\n\nIf you are using Autoinit Manager, click on \"Bone Flex Drivers\" in the Windows menu to show it.", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if dialog == QtGui.QMessageBox.Yes:
            # Close existing window
            try:
                firstWindow.close()
                firstWindow.deleteLater()
                firstWindow = None
                globals()["global_boneFlexDriversWindow"] = None
            except:
                pass
            createBoneFlexDriversWindow()
    try:
        sfmApp.ShowTabWindow("BoneFlexDriversWindow")
    except:
        pass
except Exception  as e:
    import traceback
    traceback.print_exc()        
    msgBox = QtGui.QMessageBox()
    msgBox.setText("Error: %s" % e)
    msgBox.exec_()
