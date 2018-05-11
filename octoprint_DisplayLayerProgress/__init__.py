# coding=utf-8
from __future__ import absolute_import

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin
import octoprint.printer
import octoprint.util
import re
import flask

from octoprint.events import Events

# CONSTs
from octoprint_DisplayLayerProgress import stringUtils
from octoprint_DisplayLayerProgress.LayerExpression import LayerExpression

SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES = "showAllPrinterMessages"
SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR = "showHeightInStatusBar"
SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR = "showLayerInStatusBar"
SETTINGS_KEY_SHOW_ON_PRINTERDISPLAY = "showOnPrinterDisplay"
SETTINGS_KEY_NAVBAR_MESSAGEPATTERN = "navBarMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN = "printerDisplayMessagePattern"
SETTINGS_KEY_ADD_TRAILINGCHAR = "addTrailingChar"
SETTINGS_KEY_LAYER_OFFSET = "layerOffset"
SETTINGS_KEY_TOTAL_HEIGHT_METHODE = "totalHeightMethode"
SETTINGS_KEY_LAYER_EXPRESSIONS = "layerExpressions"

HEIGHT_METHODE_Z_MAX = "zMax"
HEIGHT_METHODE_Z_EXTRUSION = "zExtrusion"

NOT_PRESENT = "-"
LAYER_MESSAGE_PREFIX = "M117 INDICATOR-Layer"
LAYER_COUNT_EXPRESSION = LAYER_MESSAGE_PREFIX + "([0-9]*)"

#LAYER_EXPRESSION_CURA = ";LAYER:([0-9]+).*"
#LAYER_EXPRESSION_S3D = "; layer ([0-9]+),.*"

# Match G1 Z149.370 F1000 or G0 F9000 X161.554 Y118.520 Z14.950     ##no comments
Z_HEIGHT_EXPRESSION = "^[^;](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)"
zHeightPattern = re.compile(Z_HEIGHT_EXPRESSION)
# Match G0 or G1 positive extrusion e.g. G1 X58.030 Y72.281 E0.1839 F2250
EXTRUSION_EXPRESSION = "G[0|1] .*E[+]*([0-9]+[.]*[0-9]*).*"
extrusionPattern = re.compile(EXTRUSION_EXPRESSION)

PROGRESS_KEYWORD_EXPRESSION = "[progress]"
CURRENT_LAYER_KEYWORD_EXPRESSION = "[current_layer]"
TOTAL_LAYER_KEYWORD_EXPRESSION = "[total_layers]"
CURRENT_HEIGHT_KEYWORD_EXPRESSION = "[current_height]"
TOTAL_HEIGHT_KEYWORD_EXPRESSION = "[total_height]"

UPDATE_DISPLAY_REASON_FRONTEND_CALL = "frontEndCall"
UPDATE_DISPLAY_REASON_HEIGHT_CHANGED = "heightChanged"
UPDATE_DISPLAY_REASON_PROGRESS_CHANGED = "progressChanged"
UPDATE_DISPLAY_REASON_LAYER_CHANGED = "layerChanged"

class LayerDetectorFileProcessor(octoprint.filemanager.util.LineProcessorStream):


    def __init__(self, fileBufferedReader, allLayerExpressions):
        super(LayerDetectorFileProcessor, self).__init__(fileBufferedReader)
        self._allLayerExpressions = allLayerExpressions
        self._currentLayerCount = 0

    def process_line(self, line):
        #line = self._checkLineForLayerComment(line, LAYER_EXPRESSION_CURA)
        #line = self._checkLineForLayerComment(line, LAYER_EXPRESSION_S3D)

        for layerExpression in self._allLayerExpressions:
            line = self._checkLineForLayerComment(line, layerExpression)

        # line = strip_comment(line).strip() DO NOT USE, because total-layer count disapears
        if not len(line):
            return None
        return line

#    def _checkLineForLayerComment(self, line, commentPattern):
    def _checkLineForLayerComment(self, line, layerExpression):
        #pattern = re.compile(commentPattern)
        pattern = layerExpression.expression
        matched = pattern.match(line)
        if matched:
            groupIndex = layerExpression.groupIndex
            if layerExpression.type_countable:
                self._currentLayerCount = self._currentLayerCount +1
                currentLayer = str(self._currentLayerCount)
            else:
                currentLayer = str(matched.group(groupIndex))
            line = line + LAYER_MESSAGE_PREFIX + currentLayer + "\r\n"
        return line


class DisplaylayerprogressPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    # my stuff
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.ProgressPlugin,
    octoprint.plugin.SimpleApiPlugin
):
    # VAR
    _layerTotalCount = NOT_PRESENT
    _currentLayer = NOT_PRESENT
    _progress = str(0)
    _currentHeight = NOT_PRESENT
    _totalHeightWithExtrusion = NOT_PRESENT
    _totalHeight = NOT_PRESENT

    def __init__(self):
        self._showProgressOnPrinterDisplay = False
        self._showLayerOnPrinterDisplay = False
        self._showHeightOnPrinterDisplay = False

        self._layerExpressionsValid = True
        self._allLayerExpressions = []

    def initialize(self):
        self._evaluatePrinterMessagePattern()
        self._parseLayerExpressions(self._settings.get([SETTINGS_KEY_LAYER_EXPRESSIONS]))

    # Modified the GCODE -> replace all Layer-Comments with G-Code Message-Comments
    def myFilePreProcessor(self, path, file_object, blinks=None, printer_profile=None, allow_overwrite=True, *args,
                           **kwargs):
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
            return file_object

        import os
        name, _ = os.path.splitext(file_object.filename)

        self._checkLayerExpressionValid()

        return octoprint.filemanager.util.StreamWrapper(file_object.filename,
                                                        LayerDetectorFileProcessor(file_object.stream(),
                                                                                   self._allLayerExpressions))

    # eval current layer from modified g-code
    def queuingGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        commandAsString = str(cmd)
        if commandAsString.startswith(LAYER_MESSAGE_PREFIX):
            layerOffset = self._settings.get_int([SETTINGS_KEY_LAYER_OFFSET])
            self._currentLayer = str(int(commandAsString[len(LAYER_MESSAGE_PREFIX):]) + layerOffset)
            self._updateDisplay(UPDATE_DISPLAY_REASON_LAYER_CHANGED)
            # filter M117 command, not needed any more
            return []
        matched = zHeightPattern.match(commandAsString)
        if matched:
            zHeight = float(matched.group(3))
            self._currentHeight = "%.2f" % zHeight
            self._updateDisplay(UPDATE_DISPLAY_REASON_HEIGHT_CHANGED)
        return

    def sentGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self._settings.get_boolean([SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES]) == True:
            commandAsString = str(cmd)
            if commandAsString.startswith("M117 "):
                printerMessage = commandAsString[len("M117 "):]
                if self._settings.get([SETTINGS_KEY_ADD_TRAILINGCHAR]):
                    printerMessage = printerMessage[:-1]

                printerMessage = "&nbsp;" + printerMessage + "&nbsp;"
                self._plugin_manager.send_plugin_message(self._identifier, dict(printerDisplay=printerMessage))
        return

    # progress-hook
    def on_print_progress(self, storage, path, progress):
        # progress 0 - 100
        self._progress = str(progress)
        self._logger.info("**** print_progress: '" + self._progress + "'")
        self._updateDisplay(UPDATE_DISPLAY_REASON_PROGRESS_CHANGED)

    # start/stop event-hook
    def on_event(self, event, payload):
        if event == Events.FILE_SELECTED:
            self._logger.info("File selected. Determining number of layers.")
            self._resetProgressValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            selectedFile = payload.get("file", "")
            markerLayerCount = LAYER_COUNT_EXPRESSION
            pattern = re.compile(markerLayerCount)

            totalHeight = 0.0
            currentHeight = 0.0
            lineNumber = 0
            self._activateBusyIndicator()
            with open(selectedFile, "r") as f:
                for line in f:
                    try:
                        lineNumber += 1
                        matched = pattern.match(line)
                        if matched:
                            layerOffset = self._settings.get_int([SETTINGS_KEY_LAYER_OFFSET])
                            self._layerTotalCount = str(int(matched.group(1)) + layerOffset)

                        matched = zHeightPattern.match(line)
                        if matched:
                            currentHeight = float(matched.group(3))
                            if currentHeight > totalHeight:
                                totalHeight = currentHeight

                        matched = extrusionPattern.match(line)
                        if matched:
                            self._totalHeightWithExtrusion = str(currentHeight)
                    except (ValueError, RuntimeError):
                        print("BOOOOOOMMMM")
                        print("#"+lineNumber + " "+line)



            if self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_MAX:
                self._totalHeight = str("%.2f" % totalHeight)
            else:
                self._totalHeight = str("%.2f" % float(self._totalHeightWithExtrusion))

            #self._totalHeight = "%.2f" % totalHeight
            #self._totalHeight = "%.2f" % self._totalHeightWithExtrusion
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.FILE_DESELECTED:
            self._resetProgressValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.PRINT_STARTED:
            self._logger.info("Printing started. Detailed progress started." + str(payload))
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)
            self._checkLayerExpressionValid()

        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self._logger.info("Printing stopped. Detailed progress stopped.")

            # send to navbar
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)
            # send to the printer
            self._sendCommandToPrinter("M117 Print Done")

        elif event == Events.CLIENT_OPENED:
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    def _resetProgressValues(self):
        # reset layer-values
        self._layerTotalCount = NOT_PRESENT
        self._currentLayer = NOT_PRESENT
        self._progress = str(0)
        self._currentHeight = NOT_PRESENT
        self._totalHeight = NOT_PRESENT
        self._totalHeightWithExtrusion = NOT_PRESENT

    def _activateBusyIndicator(self):
        self._plugin_manager.send_plugin_message(self._identifier, dict(busy=True))

    def _checkLayerExpressionValid(self):
        if self._layerExpressionsValid == False:
            self._plugin_manager.send_plugin_message(self._identifier,
                                                     dict(notifyType="error",
                                                          notifyMessage="DisplayProgressPlugin: LayerExpressions not valid! Check Plugin-Settings."))

    def _updateDisplay(self, updateReason):
        currentValueDict = {
            PROGRESS_KEYWORD_EXPRESSION: self._progress,
            CURRENT_LAYER_KEYWORD_EXPRESSION: self._currentLayer,
            TOTAL_LAYER_KEYWORD_EXPRESSION: self._layerTotalCount,
            CURRENT_HEIGHT_KEYWORD_EXPRESSION: self._currentHeight,
            TOTAL_HEIGHT_KEYWORD_EXPRESSION: self._totalHeight
        }
        printerMessagePattern = self._settings.get([SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN])
        printerMessageCommand = "M117 " + stringUtils.multiple_replace(printerMessagePattern, currentValueDict)

        navBarMessagePattern = self._settings.get([SETTINGS_KEY_NAVBAR_MESSAGEPATTERN])
        navBarMessage = stringUtils.multiple_replace(navBarMessagePattern, currentValueDict)

        # the stateMessage-format is fixed
        stateMessage = self._currentLayer + " / " + self._layerTotalCount
        # the heightMessage-format is fixed
        heightMessage = self._currentHeight + " / " + self._totalHeight
        if not self._totalHeight == NOT_PRESENT:
            heightMessage += "mm"
        # Send to PRINTER
        if self._settings.get([SETTINGS_KEY_SHOW_ON_PRINTERDISPLAY]):
            # Optimization, update only if definied in message-pattern
            shouldSendToPrinter = False
            if updateReason == UPDATE_DISPLAY_REASON_PROGRESS_CHANGED and self._showProgressOnPrinterDisplay == True:
                shouldSendToPrinter = True
            elif updateReason == UPDATE_DISPLAY_REASON_HEIGHT_CHANGED and self._showHeightOnPrinterDisplay == True:
                shouldSendToPrinter = True
            elif updateReason == UPDATE_DISPLAY_REASON_LAYER_CHANGED and self._showLayerOnPrinterDisplay == True:
                shouldSendToPrinter = True
            elif updateReason == UPDATE_DISPLAY_REASON_FRONTEND_CALL:
                shouldSendToPrinter = True

            if shouldSendToPrinter == True:
                self._sendCommandToPrinter(printerMessageCommand)
                self._logger.info("** GCODE:" + printerMessageCommand)

        showHeightInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR])
        showLayerInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR])
        # Send to STATEBAR and NAVBAR
        self._plugin_manager.send_plugin_message(self._identifier, dict(showHeightInStatusBar=showHeightInStatusBar,
                                                                        showLayerInStatusBar=showLayerInStatusBar,
                                                                        navBarMessage=navBarMessage,
                                                                        stateMessage=stateMessage,
                                                                        heightMessage=heightMessage))
        self._logger.info("** NavBar:" + navBarMessage)

    # printer specific command-manipulation.
    # e.g. ANET E10 cuts the last char from M117-commands, so this helper adds an additional underscore to the message
    def _sendCommandToPrinter(self, command):
        if self._settings.get([SETTINGS_KEY_ADD_TRAILINGCHAR]):
            if command.startswith("M117"):
                command += "_"
        print("Send GCode:" + command)
        self._printer.commands(command)

    def _evaluatePrinterMessagePattern(self):
        printerMessagePattern = self._settings.get([SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN])

        if PROGRESS_KEYWORD_EXPRESSION in printerMessagePattern:
            self._showProgressOnPrinterDisplay = True
        else:
            self._showProgressOnPrinterDisplay = False
        if CURRENT_LAYER_KEYWORD_EXPRESSION in printerMessagePattern \
                or TOTAL_LAYER_KEYWORD_EXPRESSION in printerMessagePattern:
            self._showLayerOnPrinterDisplay = True
        else:
            self._showLayerOnPrinterDisplay = False
        if CURRENT_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern \
                or TOTAL_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern:
            self._showHeightOnPrinterDisplay = True
        else:
            self._showHeightOnPrinterDisplay = False

    def _parseLayerExpressions(self, layerExpressionPatterns):
        result = None
        self._layerExpressionsValid = False
        if layerExpressionPatterns  != None and len(layerExpressionPatterns ) != 0:
            self._allLayerExpressions = []
            #patterns = "1		[;LAYER:([0-9]+).*]		CURA\r\n" + "1		[; layer ([0-9]+),.*]	Simplify3D\r\n" + "count	[BEGIN_LAYER_OBJECT]	KISSlicer"
            lines = layerExpressionPatterns .split("\n")
            lineIndex = 0
            try:
                for line in lines:
                    layerExpression = LayerExpression()

                    lineIndex = lineIndex + 1
                    startBracket = line.find("[")
                    endBracket = line.rfind("]")
                    expression = line[startBracket + 1:endBracket]
                    if line.startswith("count"):
                        layerExpression.type_countable = True
                    else:
                        layerExpression.type_countable = False
                        groupIndex = line[0:startBracket].strip()
                        layerExpression.groupIndex = int(groupIndex)
                    layerExpression.expression = re.compile(expression)
                    self._allLayerExpressions.append(layerExpression)
                self._layerExpressionsValid = True
            except (ValueError, RuntimeError) as error:
                errorMessage = "ERROR in LayerExpression! Line: " + str(lineIndex) + " Message: '" + str(error) + "'"
                return errorMessage

        return result

    def on_settings_save(self, data):
        # !!! data includes only the delta settings between the last save-action !!!
        layerExpressions = data.get(SETTINGS_KEY_LAYER_EXPRESSIONS)
        if not layerExpressions == None:
            result = self._parseLayerExpressions(layerExpressions)
            if result != None:
                self._plugin_manager.send_plugin_message(self._identifier, dict(notifyType="error", notifyMessage = result))

        # default save function
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._evaluatePrinterMessagePattern()
        #update new settings
        self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    # to allow the front end to trigger an update
    def on_api_get(self, request):
        if len(request.values) != 0:
            action = request.values["action"]

            if ("isResetSettingsEnabled" == action):
                return flask.jsonify(enabled="true")

            if ("resetSettings" == action):
                self._layerExpressionsValid = True
                self._settings.set([], self.get_settings_defaults())
                self._settings.save()

                return flask.jsonify(self.get_settings_defaults())

        # default/other action
        self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)


    # ~~ TemplatePlugin mixin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    # ~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            showOnNavBar=True,
            showOnPrinterDisplay=True,
            showAllPrinterMessages=True,
            navBarMessagePattern="Progress: [progress]% Layer: [current_layer] of [total_layers] Height: [current_height] of [total_height]mm",
            printerDisplayMessagePattern="[progress]% L=[current_layer]/[total_layers]",
            layerOffset=0,
            addTrailingChar=False,
            totalHeightMethode=HEIGHT_METHODE_Z_MAX,
            layerExpressions="1		[;LAYER:([0-9]+).*]		CURA\r\n"+ "1		[; layer ([0-9]+),.*]	Simplify3D\r\n"+ "count	[; BEGIN_LAYER_OBJECT.*]	KISSlicer",
            showLayerInStatusBar=True,
            showHeightInStatusBar=True
        )

    # ~~ AssetPlugin mixin
    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/DisplayLayerProgress.js",
                "js/ResetSettingsUtil.js",
                "js/jquery-numberedtextarea-js"],
            css=["css/DisplayLayerProgress.css",
                 "css/jquery-numberedtextarea.css"],
            less=["less/DisplayLayerProgress.less"]
        )

    # ~~ Softwareupdate hook
    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
        # for details.
        return dict(
            DisplayLayerProgress=dict(
                displayName="DisplayLayerProgress Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="OllisGit",
                repo="OctoPrint-DisplayLayerProgress",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/{target_version}.zip"
            )
        )


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "DisplayLayerProgress Plugin"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = DisplaylayerprogressPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.queuingGCodeHook,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sentGCodeHook,
        "octoprint.filemanager.preprocessor": __plugin_implementation__.myFilePreProcessor
    }
