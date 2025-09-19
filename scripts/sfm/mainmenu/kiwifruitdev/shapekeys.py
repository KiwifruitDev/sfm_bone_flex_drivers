# Shape Keys Window for Source Filmmaker (SFM)
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

shapeKeysWindow = None
shapeKeysVersion = "0.1.2"

class ShapeKeysWindow(QtGui.QWidget):
    def __init__(self):
        """
        Initialize the Shape Keys Window UI and state.
        Sets up all widgets, layouts, and connects signals.
        """
        super(ShapeKeysWindow, self).__init__()
        self.flexesInUse = []
        self.currentlyRefreshing = False
        self.currentShot = "shot1"
        self.currentAnimationSet = "shot1"
        self.currentShapeKeyUniqueId = "00000000-0000-0000-0000-000000000000"

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
        self.refreshButton.setToolTip("Regenerate the shape key operators and refresh the list of shots, animation sets, and shape keys")
        self.controlPanel.addStretch(1)
        self.controlPanel.addWidget(self.refreshButton, 0, QtCore.Qt.AlignRight)
        self.refreshButton.clicked.connect(self.refreshShapeKeys)
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

        # Shape keys are relationships between flexes and bones in an animation set
        # Each shape key has a flex and a bone associated with an animation set
        # Shape Key -> Animation Set -> Flex & Bone

        # Top layout: Table of shape keys
        self.shapeKeysTable = QtGui.QTableWidget()
        self.shapeKeysTable.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.shapeKeysTable.setContentsMargins(0, 0, 0, 0)
        self.shapeKeysTable.setEnabled(False)
        self.shapeKeysTable.setColumnCount(6)
        self.shapeKeysTable.setHorizontalHeaderLabels(["Name", "Flex", "Bone", "Value", "Active", "Unique Id"]) # active is a checkbox
        self.shapeKeysTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.shapeKeysTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.shapeKeysTable.itemSelectionChanged.connect(self.shapeKeySelectionChanged)
        self.shapeKeysTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.shapeKeysTable.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.shapeKeysTable.horizontalHeader().setResizeMode(2, QtGui.QHeaderView.Stretch)
        self.shapeKeysTable.horizontalHeader().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.shapeKeysTable.horizontalHeader().setResizeMode(4, QtGui.QHeaderView.ResizeToContents)
        self.shapeKeysTable.horizontalHeader().setResizeMode(5, QtGui.QHeaderView.ResizeToContents)
        # Hide the Unique Id column
        self.shapeKeysTable.setColumnHidden(3, True) # value is unused
        self.shapeKeysTable.setColumnHidden(5, True)
        self.topLayout.addWidget(self.shapeKeysTable)

        # Add load/save/add/remove buttons
        self.shapeKeysButtonsLayout = QtGui.QHBoxLayout()
        self.shapeKeysButtonsLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.addLayout(self.shapeKeysButtonsLayout)
        self.loadShapeKeysButton = QtGui.QPushButton("Import")
        self.loadShapeKeysButton.setEnabled(False)
        self.loadShapeKeysButton.setToolTip("Load shape keys from a JSON file")
        self.loadShapeKeysButton.clicked.connect(self.loadShapeKeys)
        self.shapeKeysButtonsLayout.addWidget(self.loadShapeKeysButton)
        self.saveShapeKeysButton = QtGui.QPushButton("Export")
        self.saveShapeKeysButton.setEnabled(False)
        self.saveShapeKeysButton.setToolTip("Save shape keys to a JSON file")
        self.saveShapeKeysButton.clicked.connect(self.saveShapeKeys)
        self.shapeKeysButtonsLayout.addWidget(self.saveShapeKeysButton)
        self.addShapeKeyButton = QtGui.QPushButton("Add")
        self.addShapeKeyButton.setEnabled(False)
        self.addShapeKeyButton.setToolTip("Add a new shape key")
        self.addShapeKeyButton.clicked.connect(self.addShapeKey)
        self.shapeKeysButtonsLayout.addWidget(self.addShapeKeyButton)
        self.removeShapeKeyButton = QtGui.QPushButton("Remove")
        self.removeShapeKeyButton.setEnabled(False)
        self.removeShapeKeyButton.setToolTip("Remove the selected shape key")
        self.removeShapeKeyButton.clicked.connect(self.removeShapeKey)
        self.shapeKeysButtonsLayout.addWidget(self.removeShapeKeyButton)
        self.shapeKeysButtonsLayout.addStretch()

        # Bottom layout: Deactivated until a shape key is selected
        # Show controls for the selected shape key:
        # Name (QLineEdit)
        # Active (QCheckBox)
        # Flex (QComboBox, to be populated with flexes from the animation set)
        # Min Flex Range (QDoubleSpinBox), Max Flex Range (QDoubleSpinBox)
        # Bone (QComboBox, to be populated with bones from the animation set)
        # Bone Axis (QComboBox with X, Y, Z)
        # Min Bone Range (QDoubleSpinBox), Max Bone Range (QDoubleSpinBox), Clamp (QCheckBox)
        self.shapeKeyDetailsGroup = QtGui.QGroupBox()
        self.shapeKeyDetailsGroup.setFlat(False)
        self.shapeKeyDetailsGroup.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.shapeKeyDetailsGroup.setContentsMargins(0, 0, 0, 0)
        self.shapeKeyDetailsGroup.setEnabled(False)
        self.bottomLayout.addWidget(self.shapeKeyDetailsGroup)
        self.shapeKeyDetailsLayout = QtGui.QFormLayout()
        self.shapeKeyDetailsLayout.setContentsMargins(5, 5, 5, 5)
        self.shapeKeyDetailsGroup.setLayout(self.shapeKeyDetailsLayout)
        self.shapeKeyNameEdit = QtGui.QLineEdit()
        self.shapeKeyNameEdit.setToolTip("Name of the shape key")
        self.shapeKeyNameEdit.textChanged.connect(self.shapeKeyNameChanged)
        self.shapeKeyDetailsLayout.addRow("Name:", self.shapeKeyNameEdit)
        self.shapeKeyActiveCheckbox = QtGui.QCheckBox()
        self.shapeKeyActiveCheckbox.setToolTip("Whether this shape key is active. When active, animation for the chosen flex will be disabled in order to be controlled by this shape key.")
        self.shapeKeyActiveCheckbox.stateChanged.connect(self.shapeKeyActiveChanged)
        self.shapeKeyDetailsLayout.addRow("Active:", self.shapeKeyActiveCheckbox)
        self.flexEdit = QtGui.QComboBox()
        self.flexEdit.setToolTip("Select the flex to control")
        self.flexEdit.currentIndexChanged.connect(self.flexChanged)
        self.shapeKeyDetailsLayout.addRow("Flex:", self.flexEdit)
        self.minFlexRangeSpin = QtGui.QDoubleSpinBox()
        self.minFlexRangeSpin.setToolTip("Minimum flex value")
        self.minFlexRangeSpin.setRange(-1.0, 1.0)
        self.minFlexRangeSpin.setSingleStep(0.01)
        self.minFlexRangeSpin.valueChanged.connect(self.minFlexRangeChanged)
        self.shapeKeyDetailsLayout.addRow("Min Flex Range:", self.minFlexRangeSpin)
        self.maxFlexRangeSpin = QtGui.QDoubleSpinBox()
        self.maxFlexRangeSpin.setToolTip("Maximum flex value")
        self.maxFlexRangeSpin.setRange(-1.0, 1.0)
        self.maxFlexRangeSpin.setSingleStep(0.01)
        self.maxFlexRangeSpin.valueChanged.connect(self.maxFlexRangeChanged)
        self.shapeKeyDetailsLayout.addRow("Max Flex Range:", self.maxFlexRangeSpin)
        self.boneEdit = QtGui.QComboBox()
        self.boneEdit.setToolTip("Select the bone to influence the flex value.")
        self.boneEdit.currentIndexChanged.connect(self.boneChanged)
        self.shapeKeyDetailsLayout.addRow("Bone:", self.boneEdit)
        self.boneAxisEdit = QtGui.QComboBox()
        self.boneAxisEdit.setToolTip("Select the axis of rotation for this bone.")
        self.boneAxisEdit.addItems(["X", "Y", "Z"])
        self.boneAxisEdit.currentIndexChanged.connect(self.boneAxisChanged)
        self.shapeKeyDetailsLayout.addRow("Bone Axis:", self.boneAxisEdit)
        self.minBoneRangeSpin = QtGui.QDoubleSpinBox()
        self.minBoneRangeSpin.setToolTip("The minimum rotation on the chosen axis for this bone for the flex value to reach 0.")
        self.minBoneRangeSpin.setRange(-360.0, 360.0)
        self.minBoneRangeSpin.setSingleStep(1.0)
        self.minBoneRangeSpin.valueChanged.connect(self.minBoneRangeChanged)
        self.shapeKeyDetailsLayout.addRow("Min Bone Range:", self.minBoneRangeSpin)
        self.maxBoneRangeSpin = QtGui.QDoubleSpinBox()
        self.maxBoneRangeSpin.setToolTip("The maximum rotation on the chosen axis for this bone for the flex value to reach 1.")
        self.maxBoneRangeSpin.setRange(-360.0, 360.0)
        self.maxBoneRangeSpin.setSingleStep(1.0)
        self.maxBoneRangeSpin.valueChanged.connect(self.maxBoneRangeChanged)
        self.shapeKeyDetailsLayout.addRow("Max Bone Range:", self.maxBoneRangeSpin)
        self.clampCheckbox = QtGui.QCheckBox()
        self.clampCheckbox.setToolTip("Keeps the flex value within its min/max range, even if the bone value goes beyond its limits. Prevents extreme or unwanted flex movement.")
        self.clampCheckbox.stateChanged.connect(self.clampChanged)
        self.shapeKeyDetailsLayout.addRow("Clamp:", self.clampCheckbox)

        # Status bar
        self.statusBar = QtGui.QLabel()
        self.statusBar.setText("SFM Shape Keys by KiwifruitDev v%s" % shapeKeysVersion)
        self.layout.addWidget(self.statusBar)

        self.refreshShapeKeys()
    def generateOperators(self):
        """
        Regenerates SFM operators for all shape keys in all shots.
        Handles undo context safely.
        """
        undoDisabled = False
        if dm.IsUndoEnabled():
            dm.SetUndoEnabled(False)
            undoDisabled = True
        shots = sfmApp.GetShots()
        for shot in shots:
            for i in range(shot.operators.count()):
                shot.operators.remove(0)
            shapeKeys = getattr(shot, "shapeKeys", None)
            if shapeKeys is None:
                continue
            for i in range(shapeKeys.count()):
                generatedOperators = getattr(shapeKeys[i], "generatedOperators", None)
                if generatedOperators is None:
                    continue
                # Clear existing operators
                while generatedOperators.count() > 0:
                    generatedOperators.remove(0)
                # Create new operators based on the shape key properties
                prefix = shapeKeys[i].GetName() + "_" + shapeKeys[i].animationSet.GetName() + "_" + shapeKeys[i].boneName.GetValue() + "_" + shapeKeys[i].flexName.GetValue() + "_"
                transform = vs.CreateElement("DmeConnectionOperator", (prefix + "transform").encode('utf-8'), shot.GetFileId())
                transform = generatedOperators[generatedOperators.AddToTail(transform)]
                transformInput = vs.CreateElement("DmeAttributeReference", (prefix + "transform_input").encode('utf-8'), shot.GetFileId())
                transform.SetValue("input", transformInput)
                invalidAnimationSet = False
                for j in range(shapeKeys[i].animationSet.controls.count()):
                    if getattr(shapeKeys[i].animationSet, "gameModel", None) is None:
                        # remove this shape key, as its animation set is invalid
                        shapeKeys.remove(i)
                        invalidAnimationSet = True
                        break
                    if shapeKeys[i].animationSet.controls[j].GetName() == shapeKeys[i].flexName.GetValue() or shapeKeys[i].animationSet.controls[j].GetName() == (shapeKeys[i].flexName.GetValue().replace("left_", "")) or shapeKeys[i].animationSet.controls[j].GetName() == (shapeKeys[i].flexName.GetValue().replace("right_", "")):
                        newValue = "flexWeight"
                        if shapeKeys[i].active.GetValue():
                            newValue = "disabled"
                        if not hasattr(shapeKeys[i].animationSet.controls[j], "channel"):
                            if shapeKeys[i].flexName.GetValue().startswith("left_"):
                                shapeKeys[i].animationSet.controls[j].leftvaluechannel.toAttribute.SetValue(newValue)
                            elif shapeKeys[i].flexName.GetValue().startswith("right_"):
                                shapeKeys[i].animationSet.controls[j].rightvaluechannel.toAttribute.SetValue(newValue)
                        else:
                            shapeKeys[i].animationSet.controls[j].channel.toAttribute.SetValue(newValue)
                    if shapeKeys[i].animationSet.controls[j].GetName() == shapeKeys[i].boneName.GetValue():
                        transformInput.SetValue("element", shapeKeys[i].animationSet.controls[j].orientationChannel.toElement)
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
                isY = "rtod(asin(clamp(2*(w*y - z*x), -1, 1)))"
                isZ = "rtod(atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))"
                axisExpr = {"X": isX, "Y": isY, "Z": isZ}.get(shapeKeys[i].boneAxis.GetValue().upper(), isX)
                axisExpr = "ramp(%s, %f, %f)" % (axisExpr, shapeKeys[i].minBoneRange.GetValue(), shapeKeys[i].maxBoneRange.GetValue())
                if shapeKeys[i].clamp.GetValue():
                    axisExpr = "clamp(%s, 0, 1)" % axisExpr
                # Map flex range from minFlexRange to maxFlexRange
                axisExpr = "lerp(%s, %f, %f)" % (axisExpr, shapeKeys[i].minFlexRange.GetValue(), shapeKeys[i].maxFlexRange.GetValue())
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
                for j in range(shapeKeys[i].animationSet.gameModel.globalFlexControllers.count()):
                    if shapeKeys[i].animationSet.gameModel.globalFlexControllers[j].GetName() == shapeKeys[i].flexName.GetValue():
                        resultOutput.SetValue("element", shapeKeys[i].animationSet.gameModel.globalFlexControllers[j])
                        break
                resultOutput.attribute.SetValue("flexWeight")
                if shapeKeys[i].active.GetValue():
                    for j in range(generatedOperators.count()):
                        shot.operators.AddToTail(generatedOperators[j])
        if undoDisabled:
            dm.SetUndoEnabled(True)

    def refreshShapeKeys(self):
        if self.currentlyRefreshing == True:
            return
        self.currentlyRefreshing = True
        self.flexesInUse = []
        hasDocument = sfmApp.HasDocument()
        self.shotDropdown.clear()
        self.animationSetDropdown.clear()
        self.shapeKeysTable.setRowCount(0)
        self.shotDropdown.setEnabled(hasDocument)
        self.animationSetDropdown.setEnabled(False)
        self.shapeKeysTable.setEnabled(False)
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
        self.shapeKeysTable.setRowCount(0)
        self.shapeKeysTable.setEnabled(False)
        self.loadShapeKeysButton.setEnabled(False)
        self.saveShapeKeysButton.setEnabled(False)
        self.addShapeKeyButton.setEnabled(False)
        self.removeShapeKeyButton.setEnabled(False)
        self.shapeKeyDetailsGroup.setEnabled(False)
        if index < 0:
            return
        # shot.shapeKeys is an array of shape keys, each have an animationSet element with a name attribute
        # get all of the shot's shapeKeys and filter them by the selected animation set
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.itemText(index)
        self.currentAnimationSet = animSetName
        shots = sfmApp.GetShots()
        addedShapeKey = False
        undoDisabled = False
        if dm.IsUndoEnabled():
            dm.SetUndoEnabled(False)
            undoDisabled = True
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                # if shapeKeys is None, create it
                if shapeKeys is None:
                    shapeKeys = shot.AddAttribute("shapeKeys", vs.AT_ELEMENT_ARRAY)
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].animationSet.GetName() == animSetName:
                        # Get shape key properties
                        active = shapeKeys[i].active.GetValue()
                        flexName = shapeKeys[i].flexName.GetValue()
                        boneName = shapeKeys[i].boneName.GetValue()
                        self.flexesInUse.append(flexName)
                        # Populate the table with this shape key
                        rowPosition = self.shapeKeysTable.rowCount()
                        self.shapeKeysTable.insertRow(rowPosition)
                        nameItem = QtGui.QTableWidgetItem(shapeKeys[i].name.GetValue())
                        nameItem.setFlags(nameItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.shapeKeysTable.setItem(rowPosition, 0, nameItem)
                        flexItem = QtGui.QTableWidgetItem(flexName)
                        flexItem.setFlags(flexItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.shapeKeysTable.setItem(rowPosition, 1, flexItem)
                        boneItem = QtGui.QTableWidgetItem(boneName)
                        boneItem.setFlags(boneItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.shapeKeysTable.setItem(rowPosition, 2, boneItem)
                        valueItem = QtGui.QTableWidgetItem("0.0")
                        valueItem.setFlags(valueItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.shapeKeysTable.setItem(rowPosition, 3, valueItem)
                        uniqueId = shapeKeys[i].GetId().__str__()
                        activeCheckBox = QtGui.QCheckBox()
                        activeCheckBox.setChecked(active)
                        activeCheckBox.toggled.connect(lambda checked, uniqueId=uniqueId: self.onShapeKeyActiveChanged(checked, uniqueId))
                        self.shapeKeysTable.setCellWidget(rowPosition, 4, activeCheckBox)
                        uniqueIdItem = QtGui.QTableWidgetItem(uniqueId)
                        uniqueIdItem.setFlags(uniqueIdItem.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.shapeKeysTable.setItem(rowPosition, 5, uniqueIdItem)
                        addedShapeKey = True
                        if self.currentShapeKeyUniqueId == uniqueId:
                            self.shapeKeysTable.selectRow(rowPosition)
                break
        self.shapeKeysTable.setEnabled(True)
        self.loadShapeKeysButton.setEnabled(True)
        self.addShapeKeyButton.setEnabled(True)
        if addedShapeKey:
            self.saveShapeKeysButton.setEnabled(True)
        if undoDisabled:
            dm.SetUndoEnabled(True)
    def shapeKeySelectionChanged(self):
        # get selection
        selectedItems = self.shapeKeysTable.selectedItems()
        if not selectedItems:
            self.shapeKeyDetailsGroup.setEnabled(False)
            self.removeShapeKeyButton.setEnabled(False)
            return
        self.shapeKeyDetailsGroup.setEnabled(True)
        self.removeShapeKeyButton.setEnabled(True)
        selectedRow = selectedItems[0].row()
        uniqueIdItem = self.shapeKeysTable.item(selectedRow, 5)
        self.currentShapeKeyUniqueId = uniqueIdItem.text()
        # Populate the details panel with the selected shape key's properties
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        # Found the shape key, populate details
                        self.shapeKeyNameEdit.setText(shapeKeys[i].name.GetValue())
                        self.shapeKeyActiveCheckbox.setChecked(shapeKeys[i].active.GetValue())
                        # Populate flex dropdown
                        matchingFlex = shapeKeys[i].flexName.GetValue()
                        self.flexEdit.clear()
                        flexes = []
                        storeFlexesInUse = self.flexesInUse[:]
                        self.flexesInUse =  []
                        if shapeKeys[i].animationSet:
                            for j in range(shapeKeys[i].animationSet.gameModel.globalFlexControllers.count()):
                                if shapeKeys[i].animationSet.gameModel.globalFlexControllers[j] is None:
                                    continue
                                flexName = shapeKeys[i].animationSet.gameModel.globalFlexControllers[j].GetName()
                                self.flexEdit.addItem(flexName)
                                flexes.append(flexName.replace("left_", "").replace("right_", ""))
                                if shapeKeys[i].animationSet.gameModel.globalFlexControllers[j].GetName() == matchingFlex:
                                    self.flexEdit.setCurrentIndex(self.flexEdit.count() - 1)
                        self.flexesInUse = storeFlexesInUse + [matchingFlex] # workaround to prevent conflict errors when setting up properties
                        self.minFlexRangeSpin.setValue(shapeKeys[i].minFlexRange.GetValue() if hasattr(shapeKeys[i], "minFlexRange") else 0.0)
                        self.maxFlexRangeSpin.setValue(shapeKeys[i].maxFlexRange.GetValue() if hasattr(shapeKeys[i], "maxFlexRange") else 1.0)
                        # Populate bone dropdown
                        matchingBone = shapeKeys[i].boneName.GetValue()
                        self.boneEdit.clear()
                        if shapeKeys[i].animationSet:
                            for j in range(shapeKeys[i].animationSet.controls.count()):
                                if shapeKeys[i].animationSet.controls[j] is None:
                                    continue
                                # the name cannot be the same as a flex
                                if shapeKeys[i].animationSet.controls[j].GetName() not in flexes:
                                    self.boneEdit.addItem(shapeKeys[i].animationSet.controls[j].GetName())
                                    if shapeKeys[i].animationSet.controls[j].GetName() == matchingBone:
                                        self.boneEdit.setCurrentIndex(self.boneEdit.count() - 1)
                        axis = shapeKeys[i].boneAxis.GetValue().upper() if hasattr(shapeKeys[i], "boneAxis") else "X"
                        axisIndex = {"X": 0, "Y": 1, "Z": 2}.get(axis, 0)
                        self.boneAxisEdit.setCurrentIndex(axisIndex)
                        self.minBoneRangeSpin.setValue(shapeKeys[i].minBoneRange.GetValue() if hasattr(shapeKeys[i], "minBoneRange") else 0.0)
                        self.maxBoneRangeSpin.setValue(shapeKeys[i].maxBoneRange.GetValue() if hasattr(shapeKeys[i], "maxBoneRange") else 90.0)
                        self.clampCheckbox.setChecked(shapeKeys[i].clamp.GetValue() if hasattr(shapeKeys[i], "clamp") else True)
                        break
    def loadShapeKeys(self):
        """
        Loads shape keys from a JSON file and adds them to the current animation set.
        Provides error handling and validation.
        """
        # Load shape keys from a JSON file and add them to the current animation set
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        options = QtGui.QFileDialog.Options()
        options |= QtGui.QFileDialog.DontUseNativeDialog
        fileName, _ = QtGui.QFileDialog.getOpenFileName(self, "Load Shape Keys", "", "JSON Files (*.json);;All Files (*)", options=options)
        if fileName:
            undoDisabled = False
            if dm.IsUndoEnabled():
                dm.SetUndoEnabled(False)
                undoDisabled = True
            try:
                with open(fileName, 'r') as f:
                    shapeKeysToLoad = json.load(f)
                if not isinstance(shapeKeysToLoad, list):
                    QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Invalid shape keys file format. Expected a list of shape keys.")
                    return
                shots = sfmApp.GetShots()
                for shot in shots:
                    if shot.GetName() == shotName:
                        shapeKeys = getattr(shot, "shapeKeys", None)
                        if shapeKeys is None:
                            shapeKeys = shot.AddAttribute("shapeKeys", vs.AT_ELEMENT_ARRAY)
                        for shapeKeyData in shapeKeysToLoad:
                            if not isinstance(shapeKeyData, dict):
                                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Malformed shape key entry: %s" % str(shapeKeyData))
                                continue
                            name = shapeKeyData.get("name", "").strip()
                            flexName = shapeKeyData.get("flexName", "").strip()
                            boneName = shapeKeyData.get("boneName", "").strip()
                            if not name or not flexName or not boneName:
                                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Missing required fields in shape key: %s" % str(shapeKeyData))
                                continue
                            if flexName in self.flexesInUse:
                                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Could not import Shape Key '%s'\nFlex '%s' is already in use by another shape key" % (name, flexName))
                                continue
                            newShapeKey = vs.CreateElement("DmElement", name.encode('utf-8'), shot.GetFileId())
                            newShapeKey = shapeKeys[shapeKeys.AddToTail(newShapeKey)]
                            newShapeKey.AddAttribute("active", vs.AT_BOOL).SetValue(shapeKeyData.get("active", True))
                            newShapeKey.AddAttribute("flexName", vs.AT_STRING).SetValue(flexName.encode('utf-8'))
                            newShapeKey.AddAttribute("boneName", vs.AT_STRING).SetValue(boneName.encode('utf-8'))
                            newShapeKey.AddAttribute("minFlexRange", vs.AT_FLOAT).SetValue(shapeKeyData.get("minFlexRange", 0.0))
                            newShapeKey.AddAttribute("maxFlexRange", vs.AT_FLOAT).SetValue(shapeKeyData.get("maxFlexRange", 1.0))
                            newShapeKey.AddAttribute("boneAxis", vs.AT_STRING).SetValue(shapeKeyData.get("boneAxis", "X").upper().encode('utf-8'))
                            newShapeKey.AddAttribute("minBoneRange", vs.AT_FLOAT).SetValue(shapeKeyData.get("minBoneRange", 0.0))
                            newShapeKey.AddAttribute("maxBoneRange", vs.AT_FLOAT).SetValue(shapeKeyData.get("maxBoneRange", 90.0))
                            newShapeKey.AddAttribute("clamp", vs.AT_BOOL).SetValue(shapeKeyData.get("clamp", True))
                            newShapeKey.AddAttribute("generatedOperators", vs.AT_ELEMENT_ARRAY)
                            animationSetAttribute = newShapeKey.AddAttribute("animationSet", vs.AT_ELEMENT)
                            for i in range(shot.animationSets.count()):
                                if shot.animationSets[i].GetName() == animSetName:
                                    animationSetAttribute.SetValue(shot.animationSets[i])
                                    break
                            self.flexesInUse.append(flexName)
            except Exception as e:
                QtGui.QMessageBox.critical(self, "Shape Keys: Error", "Failed to load shape keys: %s" % str(e))
            if undoDisabled:
                dm.SetUndoEnabled(True)
            self.refreshShapeKeys()
            self.animationSetChanged(self.animationSetDropdown.currentIndex())
    def saveShapeKeys(self):
        # Save the current animation set's shape keys to a JSON file
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    QtGui.QMessageBox.warning(self, "Shape Keys: Error", "No shape keys to save")
                    return
                shapeKeysToSave = []
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].animationSet.GetName() == animSetName:
                        shapeKeyData = {
                            "name": shapeKeys[i].name.GetValue(),
                            "active": shapeKeys[i].active.GetValue(),
                            "flexName": shapeKeys[i].flexName.GetValue(),
                            "boneName": shapeKeys[i].boneName.GetValue(),
                            "minFlexRange": shapeKeys[i].minFlexRange.GetValue() if hasattr(shapeKeys[i], "minFlexRange") else 0.0,
                            "maxFlexRange": shapeKeys[i].maxFlexRange.GetValue() if hasattr(shapeKeys[i], "maxFlexRange") else 1.0,
                            "boneAxis": shapeKeys[i].boneAxis.GetValue() if hasattr(shapeKeys[i], "boneAxis") else "X",
                            "minBoneRange": shapeKeys[i].minBoneRange.GetValue() if hasattr(shapeKeys[i], "minBoneRange") else 0.0,
                            "maxBoneRange": shapeKeys[i].maxBoneRange.GetValue() if hasattr(shapeKeys[i], "maxBoneRange") else 90.0,
                            "clamp": shapeKeys[i].clamp.GetValue() if hasattr(shapeKeys[i], "clamp") else True,
                        }
                        shapeKeysToSave.append(shapeKeyData)
                if not shapeKeysToSave:
                    QtGui.QMessageBox.warning(self, "Shape Keys: Error", "No shape keys to save for the selected animation set")
                    return
                options = QtGui.QFileDialog.Options()
                options |= QtGui.QFileDialog.DontUseNativeDialog
                fileName, _ = QtGui.QFileDialog.getSaveFileName(self, "Save Shape Keys", "", "JSON Files (*.json);;All Files (*)", options=options)
                if fileName:
                    try:
                        # Append .json extension if not present
                        if not fileName.lower().endswith('.json'):
                            fileName += '.json'
                        with open(fileName, 'w') as f:
                            json.dump(shapeKeysToSave, f, indent=4)
                        QtGui.QMessageBox.information(self, "Shape Keys: Success", "Shape keys saved successfully")
                    except Exception as e:
                        QtGui.QMessageBox.critical(self, "Shape Keys: Error", "Failed to save shape keys: %s" % str(e))
    def addShapeKey(self):
        # Dialog box to set name and select flex/bone
        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle("Add Shape Key")
        dialogLayout = QtGui.QFormLayout()
        dialog.setLayout(dialogLayout)
        nameEdit = QtGui.QLineEdit()
        nameEdit.setText("shapeKey%d" % (self.shapeKeysTable.rowCount() + 1))
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
                            # the name cannot be the same as a flex
                            if shot.animationSets[i].controls[j].GetName() not in flexes:
                                boneEdit.addItem(shot.animationSets[i].controls[j].GetName())
                        break
                break
        if dialog.exec_() == QtGui.QDialog.Accepted:
            name = nameEdit.text().strip()
            flexName = flexEdit.currentText()
            boneName = boneEdit.currentText()
            if not name:
                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Name cannot be empty")
                return
            if not flexName:
                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Flex must be selected")
                return
            if flexName in self.flexesInUse:
                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Flex '%s' is already in use by another shape key" % flexName)
                return
            if not boneName:
                QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Bone must be selected")
                return
            # Add the shape key to the shot's shapeKeys array
            undoDisabled = False
            if dm.IsUndoEnabled():
                dm.SetUndoEnabled(False)
                undoDisabled = True
            for shot in shots:
                if shot.GetName() == shotName:
                    shapeKeys = getattr(shot, "shapeKeys", None)
                    if shapeKeys is None:
                        shapeKeys = shot.AddAttribute("shapeKeys", vs.AT_ELEMENT_ARRAY)
                    newShapeKey = vs.CreateElement("DmElement", name.encode('utf-8'), shot.GetFileId())
                    newShapeKey.AddAttribute("active", vs.AT_BOOL).SetValue(True)
                    newShapeKey.AddAttribute("flexName", vs.AT_STRING).SetValue(flexName.encode('utf-8'))
                    newShapeKey.AddAttribute("boneName", vs.AT_STRING).SetValue(boneName.encode('utf-8'))
                    newShapeKey.AddAttribute("minFlexRange", vs.AT_FLOAT).SetValue(0.0)
                    newShapeKey.AddAttribute("maxFlexRange", vs.AT_FLOAT).SetValue(1.0)
                    newShapeKey.AddAttribute("boneAxis", vs.AT_STRING).SetValue("X".encode('utf-8'))
                    newShapeKey.AddAttribute("minBoneRange", vs.AT_FLOAT).SetValue(0.0)
                    newShapeKey.AddAttribute("maxBoneRange", vs.AT_FLOAT).SetValue(90.0)
                    newShapeKey.AddAttribute("clamp", vs.AT_BOOL).SetValue(True)
                    newShapeKey.AddAttribute("generatedOperators", vs.AT_ELEMENT_ARRAY)
                    for i in range(shot.animationSets.count()):
                        if shot.animationSets[i].GetName() == animSetName:
                            newShapeKey.AddAttribute("animationSet", vs.AT_ELEMENT).SetValue(shot.animationSets[i])
                            break
                    shapeKeys.AddToTail(newShapeKey)
            self.refreshShapeKeys()
            if undoDisabled:
                dm.SetUndoEnabled(True)
    def removeShapeKey(self):
        if not self.currentShapeKeyUniqueId:
            return
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        undoDisabled = False
        if dm.IsUndoEnabled():
            dm.SetUndoEnabled(False)
            undoDisabled = True
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        # Found the shape key, remove it
                        for j in range(shapeKeys[i].animationSet.controls.count()):
                            if shapeKeys[i].animationSet.controls[j] is None:
                                continue
                            if shapeKeys[i].animationSet.controls[j].GetName() == shapeKeys[i].flexName.GetValue() or shapeKeys[i].animationSet.controls[j].GetName() == shapeKeys[i].flexName.GetValue().replace("left_", "").replace("right_", ""):
                                # if channel attribute doesn't exist, find "left"/"right" + "valuechannel"
                                if not hasattr(shapeKeys[i].animationSet.controls[j], "channel"):
                                    if shapeKeys[i].flexName.GetValue().startswith("left_"):
                                        shapeKeys[i].animationSet.controls[j].leftvaluechannel.toAttribute.SetValue("flexWeight")
                                    elif shapeKeys[i].flexName.GetValue().startswith("right_"):
                                        shapeKeys[i].animationSet.controls[j].rightvaluechannel.toAttribute.SetValue("flexWeight")
                                else:
                                    shapeKeys[i].animationSet.controls[j].channel.toAttribute.SetValue("flexWeight")
                                break
                        shapeKeys.remove(i)
                        break
                break
        if undoDisabled:
            dm.SetUndoEnabled(True)
        self.currentShapeKeyUniqueId = "00000000-0000-0000-0000-000000000000"
        self.refreshShapeKeys()
    def shapeKeyNameChanged(self, text):
        # Update the name in the table and the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if shapeKeys[i].name.GetValue() == text:
                            return # no change
                        # Found the shape key, update its name
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].SetName(text.encode('utf-8'))
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        # Update the name in the table
                        for row in range(self.shapeKeysTable.rowCount()):
                            uniqueIdItem = self.shapeKeysTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                                nameItem = self.shapeKeysTable.item(row, 0)
                                nameItem.setText(text)
                        break
                break
        self.generateOperators()
    def shapeKeyActiveChanged(self, state):
        # Update the active checkbox in the table and the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].active.SetValue(state)
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        # Update the checkbox in the table
                        for row in range(self.shapeKeysTable.rowCount()):
                            uniqueIdItem = self.shapeKeysTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                                activeCheckBox = self.shapeKeysTable.cellWidget(row, 4)
                                activeCheckBox.setChecked(state)
                        break
        self.generateOperators()
    def flexChanged(self, index):
        if index < 0:
            return
        # Update the flex name in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        flexName = self.flexEdit.itemText(index)
        if flexName in self.flexesInUse and flexName != self.shapeKeysTable.item(self.shapeKeysTable.currentRow(), 1).text():
            QtGui.QMessageBox.warning(self, "Shape Keys: Error", "Flex '%s' is already in use by another shape key" % flexName)
            # revert to previous selection
            for row in range(self.shapeKeysTable.rowCount()):
                uniqueIdItem = self.shapeKeysTable.item(row, 5)
                if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                    flexItem = self.shapeKeysTable.item(row, 1)
                    currentFlexName = flexItem.text()
                    for i in range(self.flexEdit.count()):
                        if self.flexEdit.itemText(i) == currentFlexName:
                            self.flexEdit.setCurrentIndex(i)
                            break
                    break
            return
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if shapeKeys[i].flexName.GetValue() == flexName:
                            return # no change
                        # Found the shape key, update its flex name
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].flexName.SetValue(flexName.encode('utf-8'))
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        # Update the flex name in the table
                        for row in range(self.shapeKeysTable.rowCount()):
                            uniqueIdItem = self.shapeKeysTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                                flexItem = self.shapeKeysTable.item(row, 1)
                                flexItem.setText(flexName)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def minFlexRangeChanged(self, value):
        # Update the min flex range in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(shapeKeys[i], "minFlexRange") and shapeKeys[i].minFlexRange.GetValue() == value:
                            return # no change
                        # Found the shape key, update its min flex range
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        if not hasattr(shapeKeys[i], "minFlexRange"):
                            shapeKeys[i].AddAttribute("minFlexRange", vs.AT_FLOAT)
                        shapeKeys[i].minFlexRange.SetValue(value)
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def maxFlexRangeChanged(self, value):
        # Update the max flex range in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(shapeKeys[i], "maxFlexRange") and shapeKeys[i].maxFlexRange.GetValue() == value:
                            return # no change
                        # Found the shape key, update its max flex range
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        if not hasattr(shapeKeys[i], "maxFlexRange"):
                            shapeKeys[i].AddAttribute("maxFlexRange", vs.AT_FLOAT)
                        shapeKeys[i].maxFlexRange.SetValue(value)
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def boneChanged(self, index):
        if index < 0:
            return
        # Update the bone name in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        boneName = self.boneEdit.itemText(index)
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if shapeKeys[i].boneName.GetValue() == boneName:
                            return # no change
                        # Found the shape key, update its bone name
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].boneName.SetValue(boneName.encode('utf-8'))
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        # Update the bone name in the table
                        for row in range(self.shapeKeysTable.rowCount()):
                            uniqueIdItem = self.shapeKeysTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                                boneItem = self.shapeKeysTable.item(row, 2)
                                boneItem.setText(boneName)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def boneAxisChanged(self, index):
        if index < 0:
            return
        # Update the bone axis in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        boneAxis = self.boneAxisEdit.itemText(index)
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if shapeKeys[i].boneAxis.GetValue() == boneAxis:
                            return # no change
                        # Found the shape key, update its bone axis
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].boneAxis.SetValue(boneAxis.encode('utf-8'))
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        # Update the bone axis in the table
                        for row in range(self.shapeKeysTable.rowCount()):
                            uniqueIdItem = self.shapeKeysTable.item(row, 5)
                            if uniqueIdItem.text() == self.currentShapeKeyUniqueId:
                                boneAxisItem = self.shapeKeysTable.item(row, 3)
                                boneAxisItem.setText(boneAxis)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def minBoneRangeChanged(self, value):
        # Update the min bone range in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(shapeKeys[i], "minBoneRange") and shapeKeys[i].minBoneRange.GetValue() == value:
                            return # no change
                        # Found the shape key, update its min bone range
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        if not hasattr(shapeKeys[i], "minBoneRange"):
                            shapeKeys[i].AddAttribute("minBoneRange", vs.AT_FLOAT)
                        shapeKeys[i].minBoneRange.SetValue(value)
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        break
                break
        self.generateOperators()
        #self.refreshShapeKeys()
    def maxBoneRangeChanged(self, value):
        # Update the max bone range in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        undoDisabled = False
        if dm.IsUndoEnabled():
            dm.SetUndoEnabled(False)
            undoDisabled = True
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        if hasattr(shapeKeys[i], "maxBoneRange") and shapeKeys[i].maxBoneRange.GetValue() == value:
                            if undoDisabled:
                                dm.SetUndoEnabled(True)
                            return # no change
                        # Found the shape key, update its max bone range
                        if not hasattr(shapeKeys[i], "maxBoneRange"):
                            shapeKeys[i].AddAttribute("maxBoneRange", vs.AT_FLOAT)
                        shapeKeys[i].maxBoneRange.SetValue(value)
                        break
                break
        if undoDisabled:
            dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshShapeKeys()
    def clampChanged(self, state):
        # Update the clamp checkbox in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        undoDisabled = False
        if dm.IsUndoEnabled():
            dm.SetUndoEnabled(False)
            undoDisabled = True
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == self.currentShapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        shapeKeys[i].clamp.SetValue(state)
                        break
                break
        if undoDisabled:
            dm.SetUndoEnabled(True)
        self.generateOperators()
        #self.refreshShapeKeys()
    def onShapeKeyActiveChanged(self, checked, shapeKeyUniqueId):
        if self.currentShapeKeyUniqueId == shapeKeyUniqueId:
            # Update the checkbox in the details panel if it matches the current shape key
            self.shapeKeyActiveCheckbox.setChecked(checked)
            return # already handled in shapeKeyActiveChanged
        # Update the active state in the shape key object
        shotName = self.shotDropdown.currentText()
        animSetName = self.animationSetDropdown.currentText()
        shots = sfmApp.GetShots()
        for shot in shots:
            if shot.GetName() == shotName:
                shapeKeys = getattr(shot, "shapeKeys", None)
                if shapeKeys is None:
                    break
                for i in range(shapeKeys.count()):
                    if shapeKeys[i].GetId().__str__() == shapeKeyUniqueId and shapeKeys[i].animationSet.name.GetValue() == animSetName:
                        undoDisabled = False
                        if dm.IsUndoEnabled():
                            dm.SetUndoEnabled(False)
                            undoDisabled = True
                        shapeKeys[i].active.SetValue(checked)
                        if undoDisabled:
                            dm.SetUndoEnabled(True)
                        break
                break
        self.generateOperators()

def createShapeKeysWindow():
    try:
        shapeKeysWindow = ShapeKeysWindow()
        pointer = shiboken.getCppPointer(shapeKeysWindow)
        sfmApp.RegisterTabWindow("ShapeKeysWindow", "Shape Keys", pointer[0])
        globals()["global_shapeKeysWindow"] = shapeKeysWindow
    except Exception as e:
        import traceback
        traceback.print_exc()        
        msgBox = QtGui.QMessageBox()
        msgBox.setText("Error: %s" % e)
        msgBox.exec_()

try:
    # Create window if it doesn't exist
    firstWindow = globals().get("global_shapeKeysWindow")
    if firstWindow is None:
        createShapeKeysWindow()
    else:
        dialog = QtGui.QMessageBox.warning(None, "Shape Keys: Error", "The Shape Keys window is already open.\nIf you are a developer, click Yes to forcibly open a new instance.\nOtherwise, click No to close this message.\n\nIf you are using Autoinit Manager, click on \"Shape Keys\" in the Windows menu to show it.", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if dialog == QtGui.QMessageBox.Yes:
            # Close existing window
            try:
                firstWindow.close()
                firstWindow.deleteLater()
                firstWindow = None
                globals()["global_shapeKeysWindow"] = None
            except:
                pass
            createShapeKeysWindow()
    try:
        sfmApp.ShowTabWindow("ShapeKeysWindow")
    except:
        pass
except Exception  as e:
    import traceback
    traceback.print_exc()        
    msgBox = QtGui.QMessageBox()
    msgBox.setText("Error: %s" % e)
    msgBox.exec_()
