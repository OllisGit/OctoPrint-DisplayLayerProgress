# coding=utf-8
from __future__ import absolute_import

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin
import octoprint.printer
import octoprint.util
import re
from octoprint.events import Events

# CONSTs
from octoprint_DisplayLayerProgress import stringUtils

SETTINGS_KEY_SHOWON_NAVBAR = "showOnNavBar"
SETTINGS_KEY_SHOWON_PRINTERDISPLAY = "showOnPrinterDisplay"
SETTINGS_KEY_NAVBAR_MESSAGEPATTERN = "navBarMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN = "printerDisplayMessagePattern"
SETTINGS_KEY_ADD_TRAILINGCHAR = "addTrailingChar"

NOT_PRESENT = "-"
LAYER_MESSAGE_PREFIX = "M117 INDICATOR-Layer"
LAYER_EXPRESSION_CURA = ";LAYER:([0-9]+)"
LAYER_EXPRESSION_S3D = "; layer ([0-9]+),.*"
LAYER_COUNT_EXPRESSION = LAYER_MESSAGE_PREFIX + "([0-9]*)"
# Match G1 Z149.370 F1000 or G0 F9000 X161.554 Y118.520 Z14.950
Z_HEIGHT_EXPRESSION = "(.*)( Z)([+]*[0-9]+.[0-9]*)(.*)"
zHeightPattern = re.compile(Z_HEIGHT_EXPRESSION)

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
    def process_line(self, line):

        line = self._checkLineForLayerComment(line, LAYER_EXPRESSION_CURA)
        line = self._checkLineForLayerComment(line, LAYER_EXPRESSION_S3D)

        # line = strip_comment(line).strip() DO NOT USE, because total-layer count disapears
        if not len(line):
            return None
        return line

    def _checkLineForLayerComment(self, line, commentPattern):
        pattern = re.compile(commentPattern)
        matched = pattern.match(line)
        if matched:
            currentLayer = matched.group(1)
            line = LAYER_MESSAGE_PREFIX + currentLayer + "\r\n"
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
    _currentHeight = str(0)
    _totalHeight = 0.0

    def __init__(self):
        self._showProgressOnPrinterDisplay = False
        self._showLayerOnPrinterDisplay = False
        self._showHeightOnPrinterDisplay = False

    def initialize(self):
        self._evaluatePrinterMessagePattern()

    # Modified the GCODE -> replace all Layer-Comments with G-Code Message-Comments
    def myFilePreProcessor(self, path, file_object, blinks=None, printer_profile=None, allow_overwrite=True, *args,
                           **kwargs):
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
            return file_object

        import os
        name, _ = os.path.splitext(file_object.filename)

        return octoprint.filemanager.util.StreamWrapper(file_object.filename,
                                                        LayerDetectorFileProcessor(file_object.stream()))

    # eval current layer from modified g-code
    def queuingGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        commandAsString = str(cmd)
        if commandAsString.startswith(LAYER_MESSAGE_PREFIX):
            self._currentLayer = str(int(commandAsString[len(LAYER_MESSAGE_PREFIX):]) + 1)
            self._logger.info("**** g-code hook: '" + self._currentLayer + "'")
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
        if self._settings.get_boolean(["showAllPrinterMessages"]) == True:
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

            selectedFile = payload.get("file", "")
            markerLayerCount = LAYER_COUNT_EXPRESSION
            pattern = re.compile(markerLayerCount)

            totalHeight = 0.0
            lineNumber = 0
            with open(selectedFile, "r") as f:
                for line in f:
                    lineNumber += 1
                    matched = pattern.match(line)
                    if matched:
                        self._layerTotalCount = str(int(matched.group(1)) + 1)

                    matched = zHeightPattern.match(line)
                    if matched:
                        tmpHeight = float(matched.group(3))
                        if tmpHeight > totalHeight:
                            totalHeight = tmpHeight

            self._totalHeight = "%.2f" % totalHeight
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.FILE_DESELECTED:
            self._resetProgressValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.PRINT_STARTED:
            self._logger.info("Printing started. Detailed progress started." + str(payload))
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

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
        self._currentHeight = str(0)
        self._totalHeight = 0.0

    def _updateDisplay(self, updateReason):
        currentValueDict = {
            PROGRESS_KEYWORD_EXPRESSION: self._progress,
            CURRENT_LAYER_KEYWORD_EXPRESSION: self._currentLayer,
            TOTAL_LAYER_KEYWORD_EXPRESSION: self._layerTotalCount,
            CURRENT_HEIGHT_KEYWORD_EXPRESSION: self._currentHeight,
            TOTAL_HEIGHT_KEYWORD_EXPRESSION: str(self._totalHeight)
        }
        printerMessagePattern = self._settings.get([SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN])
        printerMessageCommand = "M117 " + stringUtils.multiple_replace(printerMessagePattern, currentValueDict)

        navBarMessagePattern = self._settings.get([SETTINGS_KEY_NAVBAR_MESSAGEPATTERN])
        navBarMessage = stringUtils.multiple_replace(navBarMessagePattern, currentValueDict)

        # the stateMessage-format is fixed
        stateMessage = self._currentLayer + " / " + self._layerTotalCount
        # the heightMessage-format is fixed
        heightMessage = self._currentHeight + " / " + str(self._totalHeight) + "mm"

        # Send to PRINTER
        if self._settings.get([SETTINGS_KEY_SHOWON_PRINTERDISPLAY]):
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
        # Send to STATEBAR and NAVBAR
        self._plugin_manager.send_plugin_message(self._identifier, dict(navBarMessage=navBarMessage,
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

    def on_settings_save(self, data):
        # default save function
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._evaluatePrinterMessagePattern()

    # to allow the front end to trigger an update
    def on_api_get(self, request):
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
            addTrailingChar=False
        )

    # ~~ AssetPlugin mixin
    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/DisplayLayerProgress.js"],
            css=["css/DisplayLayerProgress.css"],
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
