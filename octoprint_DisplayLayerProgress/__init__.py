# coding=utf-8
from __future__ import absolute_import

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin
import octoprint.printer
import octoprint.util
import re
import flask
from flask import Response
import json
import logging
import threading

from octoprint.events import Events, eventManager

from collections import deque
from datetime import datetime
from datetime import timedelta
# CONSTs
from octoprint_DisplayLayerProgress import stringUtils
from octoprint_DisplayLayerProgress.LayerExpression import LayerExpression

################
#### DEBUGGING FEATURE
EVENT_LOGGING_ENABLED = False

SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES = "showAllPrinterMessages"
SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR = "showHeightInStatusBar"
SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR = "showLayerInStatusBar"
SETTINGS_KEY_SHOW_ON_PRINTERDISPLAY = "showOnPrinterDisplay"
SETTINGS_KEY_UPDATE_ONLY_WHILE_PRINTING = "updatePrinterDisplayWhilePrinting"
SETTINGS_KEY_NAVBAR_MESSAGEPATTERN = "navBarMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN = "printerDisplayMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION = "printerDisplayScreenLocation"
SETTINGS_KEY_PRINTERDISPLAY_WIDTH = "printerDisplayWidth"
SETTINGS_KEY_ADD_TRAILINGCHAR = "addTrailingChar"
SETTINGS_KEY_LAYER_OFFSET = "layerOffset"
SETTINGS_KEY_TOTAL_HEIGHT_METHODE = "totalHeightMethode"
SETTINGS_KEY_LAYER_EXPRESSIONS = "layerExpressions"
SETTINGS_KEY_FEEDRATE_FACTOR = "feedrateFactor"
SETTINGS_KEY_FEEDRATE_FORMAT = "feedrateFormat"
SETTINGS_KEY_DEBUGGING_ENABLED = "debuggingEnabled"
SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT = "layerAverageDurationCount"
SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN = "layerAverageFormatPattern"
SETTINGS_KEY_ZMAX_EXPRESSION_PATTERN = "zMaxExpressionPattern"

HEIGHT_METHODE_Z_MAX = "zMax"
HEIGHT_METHODE_Z_EXTRUSION = "zExtrusion"
HEIGHT_METHODE_Z_EXPRESSION = "zExpression"

NOT_PRESENT = "-"
LAYER_MESSAGE_PREFIX = "M117 INDICATOR-Layer"
LAYER_COUNT_EXPRESSION = LAYER_MESSAGE_PREFIX + "([0-9]*)"

# Match G1 Z149.370 F1000 or G0 F9000 X161.554 Y118.520 Z14.950     ##no comments
Z_HEIGHT_EXPRESSION = "^[^;](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)"
zHeightPattern = re.compile(Z_HEIGHT_EXPRESSION)

# Match G0 or G1 positive extrusion e.g. G1 X58.030 Y72.281 E0.1839 F2250
EXTRUSION_EXPRESSION = "G[0|1] .*E[+]*([0-9]+[.]*[0-9]*).*"
extrusionPattern = re.compile(EXTRUSION_EXPRESSION)
# Match feedrate
FEEDRATE_EXPRESSION = "^G[0|1] .*F(\d*\.?\d*).*"
feedratePattern = re.compile(FEEDRATE_EXPRESSION)

# Match Fan speed
FANSPEED_EXPRESSION = "^M106.* S(\d+\.?\d*).*"

fanSpeedPattern = re.compile(FANSPEED_EXPRESSION)
FAN_OFF_EXPRESSION = "^M107.*"
fanOffPattern = re.compile(FAN_OFF_EXPRESSION)

PROGRESS_KEYWORD_EXPRESSION = "[progress]"
CURRENT_LAYER_KEYWORD_EXPRESSION = "[current_layer]"
TOTAL_LAYER_KEYWORD_EXPRESSION = "[total_layers]"
CURRENT_HEIGHT_KEYWORD_EXPRESSION = "[current_height]"
TOTAL_HEIGHT_KEYWORD_EXPRESSION = "[total_height]"
FEEDRATE_KEYWORD_EXPRESSION = "[feedrate]"
FEEDRATE_G0_KEYWORD_EXPRESSION = "[feedrate_g0]"
FEEDRATE_G1_KEYWORD_EXPRESSION = "[feedrate_g1]"
FANSPEED_KEYWORD_EXPRESSION = "[fanspeed]"
PRINTTIME_LEFT_EXPRESSION = "[printtime_left]"
LAYER_AVERAGE_DURATION_EXPRESSION = "[average_layer_duration]"
LAYER_LAST_DURATION_EXPRESSION = "[last_layer_duration]"

UPDATE_DISPLAY_REASON_FRONTEND_CALL = "frontEndCall"
UPDATE_DISPLAY_REASON_HEIGHT_CHANGED = "heightChanged"
UPDATE_DISPLAY_REASON_PROGRESS_CHANGED = "progressChanged"
UPDATE_DISPLAY_REASON_LAYER_CHANGED = "layerChanged"
UPDATE_DISPLAY_REASON_FEEDRATE_CHANGED = "feedrateChanged"
UPDATE_DISPLAY_REASON_FANSPEED_CHANGED = "fanspeedChanged"

# Same as setup.py 'plugin_identifier'
PLUGIN_KEY_PREFIX = "DisplayLayerProgress_"

MOVEMENT_ABSOLUTE = "g90_abs"
MOVEMENT_RELATIVE = "g91_real"

class LayerDetectorFileProcessor(octoprint.filemanager.util.LineProcessorStream):


    def __init__(self, fileBufferedReader, allLayerExpressions):
        super(LayerDetectorFileProcessor, self).__init__(fileBufferedReader)
        self._allLayerExpressions = allLayerExpressions
        self._currentLayerCount = 0

    def process_line(self, line):
        for layerExpression in self._allLayerExpressions:
            origLine = line
            line = self._checkLineForLayerComment(line, layerExpression)
            if line is not origLine:
                # pattern matched, skip other expressions
                break
        # line = strip_comment(line).strip() DO NOT USE, because total-layer count disapears
        if not len(line):
            return None
        return line

    def _checkLineForLayerComment(self, line, layerExpression):
        pattern = layerExpression.expression
        matched = pattern.match(line)
        if matched:
            groupIndex = layerExpression.groupIndex
            if layerExpression.type_countable:
                self._currentLayerCount = self._currentLayerCount + 1
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
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.BlueprintPlugin
):
    # VAR
    _layerTotalCount = NOT_PRESENT
    _currentLayer = NOT_PRESENT
    _progress = str(0)
    _currentHeight = NOT_PRESENT
    _totalHeightWithExtrusion = NOT_PRESENT
    _totalHeight = NOT_PRESENT
    _feedrate = NOT_PRESENT
    _feedrateG0 = NOT_PRESENT
    _feedrateG1 = NOT_PRESENT
    _fanSpeed = NOT_PRESENT
    _isPrinterRunning = False
    _layerDurationDeque = None
    _startLayerTime = None

    def __init__(self):
        self._showProgressOnPrinterDisplay = False
        self._showLayerOnPrinterDisplay = False
        self._showHeightOnPrinterDisplay = False
        self._showFeedrateOnPrinterDisplay = False
        self._showFanSpeedOnPrinterDisplay = False

        self._printTimeLeft = ""
        self._printTimeLeftInSeconds = ""
        self._lastLayerDuration = ""
        self._lastLayerDurationInSeconds = ""
        self._averageLayerDuration = ""
        self._averageLayerDurationInSeconds = ""

        self._layerExpressionsValid = True
        self._allLayerExpressions = []

        self._layerDurationDeque = None
        self._startLayerTime = None

        self._movementMode = MOVEMENT_ABSOLUTE
        self._currentHeightFloat = 0.0

    def initialize(self):
        # setup our custom logger
        logPostfix = "events"
        self._event_file_logger = logging.getLogger("octoprint.plugins." + self._settings.plugin_key + "."+logPostfix)

        from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
        event_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix=logPostfix),
                                                                when="D", backupCount=3)
        event_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        event_logging_handler.setLevel(logging.DEBUG)

        self._event_file_logger.addHandler(event_logging_handler)
        self._event_file_logger.setLevel(logging.DEBUG)
        self._event_file_logger.propagate = False

        self._layerDurationDeque = deque(maxlen=self._settings.get_int([SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT]))

        # prepare expression-settings
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

    _lastM117Command = None
    # eval current layer from modified g-code
    def sendingGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        commandAsString = str(cmd)

        self._eventLogging("SENDING-HOOK: " + commandAsString)
        # prevent double messages
        if commandAsString.startswith("M117"):
            if self._lastM117Command == commandAsString:
                # filter double M117 commands
                self._eventLogging("SENDING-HOOK DROP COMMAND: " + commandAsString)
                return []
            else:
                self._lastM117Command = commandAsString
        # layer
        if commandAsString.startswith(LAYER_MESSAGE_PREFIX):

            layerOffset = self._settings.get_int([SETTINGS_KEY_LAYER_OFFSET])
            self._currentLayer = str(int(commandAsString[len(LAYER_MESSAGE_PREFIX):]) + layerOffset)

            ## calculate time of layer printing
            layerDuration = 0
            currentTime =  datetime.now()
            if self._startLayerTime is not None:
                layerDuration = currentTime - self._startLayerTime

            self._layerDurationDeque.append(layerDuration)
            self._startLayerTime = currentTime

            self._updateDisplay(UPDATE_DISPLAY_REASON_LAYER_CHANGED)
            # filter M117 command, not needed any more
            return []

        if "G90" == gcode:
            self._movementMode = MOVEMENT_ABSOLUTE
        if "G91" == gcode:
            self._movementMode = MOVEMENT_RELATIVE

        # Z-Height
        matched = zHeightPattern.match(commandAsString)
        if matched:
            zHeight = float(matched.group(3))
            if self._movementMode == MOVEMENT_RELATIVE:
                self._currentHeightFloat = self._currentHeightFloat + zHeight
            else:
                self._currentHeightFloat = zHeight

            self._currentHeight = "%.2f" % self._currentHeightFloat
            self._updateDisplay(UPDATE_DISPLAY_REASON_HEIGHT_CHANGED)
        # feedrate
        matched = feedratePattern.match(commandAsString)
        if matched:
            feedrate = matched.group(1)
            self._feedrate = feedrate
            if commandAsString.startswith('G0'):
                self._feedrateG0 = feedrate
            if commandAsString.startswith('G1'):
                self._feedrateG1 = feedrate
            self._updateDisplay(UPDATE_DISPLAY_REASON_FEEDRATE_CHANGED)
        # fanspeed
        matched = fanSpeedPattern.match(commandAsString)
        if matched:
            fanSpeedText = matched.group(1)
            fanSpeed = float(fanSpeedText)
            if fanSpeed == 0:
                self._fanSpeed = 'Off'
            else:
                speedFloat = float(fanSpeedText)*100.0/255.0
                speed = int(round(speedFloat))
                self._fanSpeed = str(speed) + '%'
            self._updateDisplay(UPDATE_DISPLAY_REASON_FANSPEED_CHANGED)
        matched = fanOffPattern.match(commandAsString)
        if matched:
            self._fanSpeed = 'Off'
            self._updateDisplay(UPDATE_DISPLAY_REASON_FANSPEED_CHANGED)

        return


    # eval current layer from modified g-code
    def sentGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        showDesktopPrinterDisplay = self._settings.get_boolean([SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES])
        if  showDesktopPrinterDisplay == True:
            commandAsString = str(cmd)

            self._eventLogging("SENT-HOOK: " + commandAsString)
            if commandAsString.startswith("M117 "):
                printerMessage = commandAsString[len("M117 "):]
                if self._settings.get([SETTINGS_KEY_ADD_TRAILINGCHAR]):
                    printerMessage = printerMessage[:-1]

                printerMessage = "&nbsp;" + printerMessage + "&nbsp;"
                self._plugin_manager.send_plugin_message(self._identifier, dict(showDesktopPrinterDisplay=showDesktopPrinterDisplay,
                                                                                printerDisplay=printerMessage))
        return

    # progress-hook
    def on_print_progress(self, storage, path, progress):
        # progress 0 - 100
        self._progress = str(progress)
        # logging for debugging self._logger.info("**** print_progress: '" + self._progress + "'")
        self._updateDisplay(UPDATE_DISPLAY_REASON_PROGRESS_CHANGED)

    # start/stop event-hook
    def on_event(self, event, payload):
        self._eventLogging("EVENT: " + event)

        if event == Events.FILE_SELECTED:
            self._logger.info("File selected. Determining number of layers.")
            self._resetCurrentValues()
            self._resetTotalValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            selectedFile = payload.get("file", "")
            markerLayerCount = LAYER_COUNT_EXPRESSION
            pattern = re.compile(markerLayerCount)

            zMaxPattern = re.compile(self._settings.get([SETTINGS_KEY_ZMAX_EXPRESSION_PATTERN]))

            totalHeight = 0.0
            currentHeight = 0.0
            lineNumber = 0
            self._activateBusyIndicator()
            with open(selectedFile, "r") as f:
                for line in f:
                    try:
                        lineNumber += 1
                        matched = pattern.match(line)   #identify layer count
                        if matched:
                            layerOffset = self._settings.get_int([SETTINGS_KEY_LAYER_OFFSET])
                            self._layerTotalCount = str(int(matched.group(1)) + layerOffset)

                        matched = zHeightPattern.match(line)
                        if matched:
                            # don't count on negativ extrusion, see issue #76
                            if ("E-" in line) == False:
                                currentHeight = float(matched.group(3))
                                if currentHeight > totalHeight:
                                    totalHeight = currentHeight

                        matched = extrusionPattern.match(line)
                        if matched:
                            self._totalHeightWithExtrusion = str(currentHeight)

                        matched = zMaxPattern.match(line)
                        if matched != None and (self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_EXPRESSION):
                            self._totalHeight = str(matched.group(1))

                    except (ValueError, RuntimeError):
                        print("BOOOOOOMMMM")
                        print("#"+str(lineNumber) + " " + line)


            if self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_MAX:
                self._totalHeight = str("%.2f" % totalHeight)
            elif self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_EXTRUSION:
                if not self._totalHeightWithExtrusion == NOT_PRESENT:
                    self._totalHeight = str("%.2f" % float(self._totalHeightWithExtrusion))
                else:
                    self._totalHeight = NOT_PRESENT
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.FILE_DESELECTED:
            self._resetCurrentValues()
            self._resetTotalValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.PRINT_STARTED:
            self._isPrinterRunning = True
            self._logger.info("Printing started. Detailed progress started." + str(payload))
            self._resetCurrentValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)
            self._checkLayerExpressionValid()

        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self._logger.info("Printing stopped. Detailed progress stopped.")

            # send to navbar
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            self._eventLogging("event print done!")
            # not needed could be done via standard code-settings self._sendCommandToPrinter("M117 Print Done")
            self._isPrinterRunning = False
        elif event == Events.CLIENT_OPENED:
            self._initDesktopPinterDisplay()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    def _resetCurrentValues(self):
        self._currentLayer = NOT_PRESENT
        self._progress = str(0)
        self._currentHeight = NOT_PRESENT
        self._feedrate = NOT_PRESENT
        self._feedrateG0 = NOT_PRESENT
        self._feedrateG1 = NOT_PRESENT
        self._fanSpeed = NOT_PRESENT

        self._startLayerTime = None
        self._layerDurationDeque = deque(maxlen=self._settings.get_int([SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT]))
        self._currentHeightFloat = 0.0

    def _resetTotalValues(self):
        self._layerTotalCount = NOT_PRESENT
        self._totalHeight = NOT_PRESENT
        self._totalHeightWithExtrusion = NOT_PRESENT


    def _activateBusyIndicator(self):
        self._plugin_manager.send_plugin_message(self._identifier, dict(busy=True))

    def _checkLayerExpressionValid(self):
        if self._layerExpressionsValid == False:
            self._plugin_manager.send_plugin_message(self._identifier,
                                                     dict(notifyType="error",
                                                          notifyMessage="DisplayProgressPlugin: LayerExpressions not valid! Check Plugin-Settings."))


    def _initDesktopPinterDisplay(self):
        classStyle = ""
        stackDefinition = self._settings.get([SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION])
        isTop = False
        isRight = False
        if "down" in stackDefinition:
            isTop = True
        if "right" in stackDefinition:
            isRight = True

        if isTop and isRight:
            classStyle = "stack-topleft"
        if isTop and isRight == False:
            classStyle = "stack-topright"

        if isTop == False and isRight:
            classStyle = "stack-bottomleft"
        if isTop == False and isRight == False:
            classStyle = "stack-bottomright"

        showDesktopPrinterDisplay = self._settings.get([SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES])
        initDesktopDisplay =  showDesktopPrinterDisplay

        self._plugin_manager.send_plugin_message(self._identifier,
                                                 dict(initPrinterDisplay=initDesktopDisplay,
                                                      printerDisplayScreenLocation=stackDefinition,
                                                      printerDisplayWidth=self._settings.get([SETTINGS_KEY_PRINTERDISPLAY_WIDTH]),
                                                      classDefinition=classStyle
                                                      )
                                                 )

    def _updateDisplay(self, updateReason):
        self._eventLogging("UPDATE DISPLAY: " + updateReason)

        #        myPlugin = self._plugin_manager.get_plugin("DisplayLayerProgress")
        #        myPluginInfo = self._plugin_manager.get_plugin_info("DisplayLayerProgress")
        #        myImplementation = myPluginInfo.implementation
        #        myImplementation2 = DisplaylayerprogressPlugin(myPluginInfo.implementation)

        currentData = self._printer.get_current_data()

        # NOT NEEDED at the moment estPrintTime = currentData["job"]["estimatedPrintTime"]
        self._printTimeLeft = "-"
        self._printTimeLeftInSeconds = currentData["progress"]["printTimeLeft"]
        if self._printTimeLeftInSeconds is not None:
            self._printTimeLeft = stringUtils.secondsToText(self._printTimeLeftInSeconds)
        else:
            self._printTimeLeftInSeconds = "-"

        feedrate = self._calculateFeedrate(self._feedrate)
        feedrateG0 = self._calculateFeedrate(self._feedrateG0)
        feedrateG1 = self._calculateFeedrate(self._feedrateG1)

        ## calculate layer duration
        self._lastLayerDuration = "-"
        self._lastLayerDurationInSeconds = "-"
        self._averageLayerDuration = "-"
        self._averageLayerDurationInSeconds = "-"

        if len(self._layerDurationDeque) > 0:
            lastLayerDurationTimeDelta = self._layerDurationDeque[-1]
            if isinstance( lastLayerDurationTimeDelta, int):
                self._lastLayerDurationInSeconds = lastLayerDurationTimeDelta
            else:
                self._lastLayerDurationInSeconds = lastLayerDurationTimeDelta.seconds
            self._lastLayerDuration = stringUtils.strfdelta(lastLayerDurationTimeDelta, self._settings.get([SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN]))

            # avarag calc only if we have engough layer measurments
            allLayerDurationCount = len(self._layerDurationDeque)
            if allLayerDurationCount == self._settings.get_int([SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT]):
                calcAverageDuration = 0
                allLayerDurations = list(self._layerDurationDeque)

                for duration in allLayerDurations:
                    if type(duration) is timedelta:
                        calcAverageDuration = calcAverageDuration + duration.total_seconds()

                calcAverageDuration = calcAverageDuration / allLayerDurationCount
                calcAverageDurationTimeDelta = timedelta(seconds = calcAverageDuration)
                self._averageLayerDuration = stringUtils.strfdelta(calcAverageDurationTimeDelta, self._settings.get([SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN]))
                self._averageLayerDurationInSeconds = calcAverageDurationTimeDelta.seconds

        currentValueDict = {
            PROGRESS_KEYWORD_EXPRESSION: self._progress,
            CURRENT_LAYER_KEYWORD_EXPRESSION: self._currentLayer,
            TOTAL_LAYER_KEYWORD_EXPRESSION: self._layerTotalCount,
            CURRENT_HEIGHT_KEYWORD_EXPRESSION: self._currentHeight,
            TOTAL_HEIGHT_KEYWORD_EXPRESSION: self._totalHeight,
            FEEDRATE_KEYWORD_EXPRESSION: feedrate,
            FEEDRATE_G0_KEYWORD_EXPRESSION: feedrateG0,
            FEEDRATE_G1_KEYWORD_EXPRESSION: feedrateG1,
            FANSPEED_KEYWORD_EXPRESSION: self._fanSpeed,
            PRINTTIME_LEFT_EXPRESSION: self._printTimeLeft,
            LAYER_LAST_DURATION_EXPRESSION: self._lastLayerDuration,
            LAYER_AVERAGE_DURATION_EXPRESSION: self._averageLayerDuration
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
            elif updateReason == UPDATE_DISPLAY_REASON_FEEDRATE_CHANGED and self._showFeedrateOnPrinterDisplay == True:
                shouldSendToPrinter = True
            elif updateReason == UPDATE_DISPLAY_REASON_FANSPEED_CHANGED and self._showFanSpeedOnPrinterDisplay == True:
                shouldSendToPrinter = True
            elif updateReason == UPDATE_DISPLAY_REASON_FRONTEND_CALL:
                shouldSendToPrinter = True

            if self._settings.get([SETTINGS_KEY_UPDATE_ONLY_WHILE_PRINTING]):
                if self._isPrinterRunning:
                    #if self._printer.is_printing():
                    shouldSendToPrinter = True
                else:
                    shouldSendToPrinter = False

            if shouldSendToPrinter == True:
                self._sendCommandToPrinter(printerMessageCommand)

        showHeightInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR])
        showLayerInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR])

        showDesktopPrinterDisplay = self._settings.get([SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES])
        # Send to STATEBAR and NAVBAR
        self._plugin_manager.send_plugin_message(self._identifier, dict(showDesktopPrinterDisplay=showDesktopPrinterDisplay,
                                                                        showHeightInStatusBar=showHeightInStatusBar,
                                                                        showLayerInStatusBar=showLayerInStatusBar,
                                                                        navBarMessage=navBarMessage,
                                                                        stateMessage=stateMessage,
                                                                        heightMessage=heightMessage))

        # Fire Event, so that other Plugins could react on the event
        if updateReason is not UPDATE_DISPLAY_REASON_FRONTEND_CALL:
            eventKey = PLUGIN_KEY_PREFIX + updateReason
            eventPayload = dict(
                totalLayer = self._layerTotalCount,
                currentLayer = self._currentLayer,
                lastLayerDuration = self._lastLayerDuration,
                lastLayerDurationInSeconds = self._lastLayerDurationInSeconds,
                averageLayerDuration = self._averageLayerDuration,
                averageLayerDurationInSeconds = self._averageLayerDurationInSeconds,
                currentHeight = self._currentHeight,
                totalHeightWithExtrusion = self._totalHeightWithExtrusion,
                feedrate = self._feedrate,
                feedrateG0 = self._feedrateG0,
                feedrateG1 = self._feedrateG1,
                fanspeed = self._fanSpeed,
                progress =self._progress,
                printTimeLeft = self._printTimeLeft,
                printTimeLeftInSeconds = self._printTimeLeftInSeconds,
            )
            eventManager().fire(eventKey, eventPayload)
            pass

    def _calculateFeedrate(self, feedrate):
        if feedrate == "-":
            return feedrate
        feedrateFactor = self._settings.get([SETTINGS_KEY_FEEDRATE_FACTOR])
        feedrateFormat = self._settings.get([SETTINGS_KEY_FEEDRATE_FORMAT])

        newFeedrate = float(feedrateFactor) * float(feedrate)
        result = feedrateFormat.format(newFeedrate)
        return result

    # printer specific command-manipulation.
    # e.g. ANET E10 cuts the last char from M117-commands, so this helper adds an additional underscore to the message
    def _sendCommandToPrinter(self, command):
        if self._settings.get([SETTINGS_KEY_ADD_TRAILINGCHAR]):
            if command.startswith("M117"):
                command += "_"
        # logging for debugging print("Send GCode:" + command)
        self._eventLogging("SEND-COMMAND: "+command)
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
        if FEEDRATE_KEYWORD_EXPRESSION in printerMessagePattern \
                or FEEDRATE_G0_KEYWORD_EXPRESSION in printerMessagePattern \
                or FEEDRATE_G1_KEYWORD_EXPRESSION in printerMessagePattern:
            self._showFeedrateOnPrinterDisplay = True
        else:
            self._showFeedrateOnPrinterDisplay = False
        if FANSPEED_KEYWORD_EXPRESSION in printerMessagePattern:
            self._showFanSpeedOnPrinterDisplay = True
        else:
            self._showFanSpeedOnPrinterDisplay = False


    def _parseLayerExpressions(self, layerExpressionPatterns):
        result = None
        self._layerExpressionsValid = False
        if layerExpressionPatterns  is not None and len(layerExpressionPatterns ) != 0:
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

    def _eventLogging(self, logMessage):
        if EVENT_LOGGING_ENABLED or self._settings.get([SETTINGS_KEY_DEBUGGING_ENABLED]):
            threadName = threading.current_thread().name
            threadId = str(threading.current_thread().ident)
            threadPattern = "["+threadId + "::" + threadName + "]"
            self._event_file_logger.debug(logMessage + " " + threadPattern)

    def on_settings_save(self, data):
        # !!! data includes only the delta settings between the last save-action !!!

        layerExpressions = data.get(SETTINGS_KEY_LAYER_EXPRESSIONS)
        if layerExpressions is not None:
            result = self._parseLayerExpressions(layerExpressions)
            if result is not None:
                self._plugin_manager.send_plugin_message(self._identifier, dict(notifyType="error", notifyMessage = result))

        initDesktopPrinterDisplay = False
        printerDisplayScreenLocationDefinition = data.get(SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION)
        if printerDisplayScreenLocationDefinition is not None:
            try:
                json.loads("{"+printerDisplayScreenLocationDefinition+"}")
                initDesktopPrinterDisplay = True
            except:
                self._plugin_manager.send_plugin_message(self._identifier, dict(notifyType="error", notifyMessage="Printer ScreenLocation could not parsed!"))

        printerDisplayWidthDefinition = data.get(SETTINGS_KEY_PRINTERDISPLAY_WIDTH)
        if printerDisplayWidthDefinition is not None:
            initDesktopPrinterDisplay = True

        # default save function
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._evaluatePrinterMessagePattern()

        self._layerDurationDeque = deque(maxlen=self._settings.get_int([SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT]))

        if initDesktopPrinterDisplay:
            self._initDesktopPinterDisplay()
        #update new settings
        self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    # to allow the frontend to trigger an update
    def on_api_get(self, request):
        if len(request.values) != 0:
            action = request.values["action"]

            if "isResetSettingsEnabled" == action:
                return flask.jsonify(enabled="true")

            if "resetSettings" == action:
                self._layerExpressionsValid = True
                self._settings.set([], self.get_settings_defaults())
                self._settings.save()

                return flask.jsonify(self.get_settings_defaults())

        # default/other action
        self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    @octoprint.plugin.BlueprintPlugin.route("/values", methods=["GET"])
    def get_displayLayerProgressValues(self):

        # return data via the default API endpoint
        return flask.jsonify({
            "layer": {
                "total": self._layerTotalCount,
                "current": self._currentLayer,
                "averageLayerDuration": self._averageLayerDuration,
                "averageLayerDurationInSeconds": self._averageLayerDurationInSeconds,
                "lastLayerDuration": self._lastLayerDuration,
                "lastLayerDurationInSeconds": self._lastLayerDurationInSeconds
            },
            "height": {
                "total": self._totalHeight,
                "totalWithExtrusion": self._totalHeightWithExtrusion,
                "current": self._currentHeight
            },
            "fanSpeed": self._fanSpeed,
            "feedrate": self._feedrate,
            "feedrateG0": self._feedrateG0,
            "feedrateG1": self._feedrateG1,
            "print": {
                "progress": self._progress,
                "timeLeft": self._printTimeLeft,
                "timeLeftInSeconds": self._printTimeLeftInSeconds
            }
        })


    # ~~ TemplatePlugin mixin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True)
        ]

    # ~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            showOnNavBar=True,
            showOnPrinterDisplay=True,
            showAllPrinterMessages=True,
            navBarMessagePattern="Progress: <span style='display: inline-block;width:24px;'>[progress]%</span>\n"
                                 "Layer: <span style='display: inline-block;width:24px;'>[current_layer]</span> of\n"
                                 "<span style='display: inline-block;width:24px;'>[total_layers]</span>\n"
                                 "Height: <span style='display: inline-block;width:42px;'>[current_height]</span> of\n"
                                 "<span style='display: inline-block;width:42px;'>[total_height]</span>mm",
#                                 "Feedrate: [feedrate] G0: [feedrate_g0] G1: [feedrate_g1]",
            printerDisplayMessagePattern="[progress]% L=[current_layer]/[total_layers]",
            layerOffset=0,
            addTrailingChar=False,
            totalHeightMethode=HEIGHT_METHODE_Z_MAX,
            layerExpressions="1\t\t[;\s*LAYER:\s*([0-9]+).*]\t\tCURA\r\n" +
                             "1\t\t[; layer ([0-9]+),.*]\t\tSimplify3D\r\n" +
                             "1\t\t[;LAYER:([0-9]+).*]\t\tideaMaker\r\n" +
                             "count\t[; BEGIN_LAYER_OBJECT.*]\t\tKISSlicer\r\n" +
                             "count\t[;BEFORE_LAYER_CHANGE]\t\tSlic3r",
            showLayerInStatusBar=True,
            showHeightInStatusBar=True,
            updatePrinterDisplayWhilePrinting=False,
            printerDisplayScreenLocation="\"dir1\": \"up\", \"dir2\": \"right\", \"firstpos1\": 40, \"firstpos2\": 10, \"spacing1\": 0, \"spacing2\": 0",
            printerDisplayWidth="15%",
            feedrateFactor="1.0",
            feedrateFormat="{:.2f}",
            debuggingEnabled=False,
            layerAverageDurationCount=5,
            layerAverageFormatPattern="{H}h:{M:02}m:{S:02}s",
            zMaxExpressionPattern=";MAXZ:([0-9]+[.]*[0-9]*).*"
        )

    # ~~ AssetPlugin mixin
    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/DisplayLayerProgress.js",
                "js/ResetSettingsUtil.js",
                "js/jquery-numberedtextarea.js"],
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
                #pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/{target_version}.zip"
                pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/latest/download/master.zip"
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
        #"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.queuingGCodeHook,
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.sendingGCodeHook,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sentGCodeHook,
        "octoprint.filemanager.preprocessor": __plugin_implementation__.myFilePreProcessor
    }

