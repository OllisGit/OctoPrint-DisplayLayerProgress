# coding=utf-8
from __future__ import absolute_import

import os

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin
import octoprint.printer
import octoprint.util
import re
import flask
import json
import logging
import threading

from babel.dates import format_time
from octoprint.events import Events, eventManager
from octoprint.util import RepeatedTimer

from collections import deque
from datetime import datetime
from datetime import timedelta

import time

from octoprint_DisplayLayerProgress import stringUtils
from octoprint_DisplayLayerProgress.CachedSettings import CachedSettings
from octoprint_DisplayLayerProgress.CommandQueue import CommandQueue
from octoprint_DisplayLayerProgress.LayerExpression import LayerExpression

################
#### DEBUGGING FEATURE
EVENT_LOGGING_ENABLED = False

SETTINGS_KEY_ADD_LAYER_INDICATORS = "addLayerIndicators"
SETTINGS_KEY_SHOW_MISSING_LAYER_INDICATOR_WARNING = "showMissingLayerIndicatorWarning"
SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES = "showAllPrinterMessages"
# SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR = "showHeightInStatusBar"
# SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR = "showLayerInStatusBar"
SETTINGS_KEY_SHOW_ON_STATE = "showOnState"
SETTINGS_KEY_SHOW_ON_NAVBAR = "showOnNavBar"
SETTINGS_KEY_SHOW_ON_PRINTERDISPLAY = "showOnPrinterDisplay"
SETTINGS_KEY_SHOW_ON_BROWSER_TITLE = "showOnBrowserTitle"
SETTINGS_KEY_SHOW_ON_FILELIST_VIEW = "showOnFileListView"
SETTINGS_KEY_APPEND_ACTUAL_BEDTEMP_TITLE = "appendActualBedTempBrowserTitle"
SETTINGS_KEY_APPEND_TARGET_BEDTEMP_TITLE = "appendTargetBedTempBrowserTitle"
SETTINGS_KEY_UPDATE_ONLY_WHILE_PRINTING = "updatePrinterDisplayWhilePrinting"
SETTINGS_KEY_STATE_MESSAGEPATTERN = "stateMessagePattern"
SETTINGS_KEY_NAVBAR_MESSAGEPATTERN = "navBarMessagePattern"
SETTINGS_KEY_BROWSER_TITLE_MODE = "browserTitleMode"
SETTINGS_KEY_BROWSER_TITLE_MESSAGEPATTERN = "browserTitleMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN = "printerDisplayMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN_SECOND = "secondPrinterDisplayMessagePattern"
SETTINGS_KEY_PRINTERDISPLAY_TOGGLE_ENABLED = "togglePrinterDisplayEnabled"
SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION = "printerDisplayScreenLocation"
SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION_CLASS = "printerDisplayScreenLocationClass"
SETTINGS_KEY_PRINTERDISPLAY_WIDTH = "printerDisplayWidth"
SETTINGS_KEY_ADD_TRAILINGCHAR = "addTrailingChar"
SETTINGS_KEY_LAYER_OFFSET = "layerOffset"

# SETTINGS_KEY_TOTAL_HEIGHT_METHODE = "totalHeightMethode"
# SETTINGS_KEY_ZMAX_EXPRESSION_PATTERN = "zMaxExpressionPattern"

SETTINGS_KEY_LAYER_EXPRESSIONS = "layerExpressions"
SETTINGS_KEY_HEIGHT_FORMAT = "heightFormat"
SETTINGS_KEY_ETA_FORMAT = "etaFormat"
SETTINGS_KEY_FEEDRATE_FACTOR = "feedrateFactor"
SETTINGS_KEY_FEEDRATE_FORMAT = "feedrateFormat"

SETTINGS_KEY_DEBUGGING_ENABLED = "debuggingEnabled"

SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT = "layerAverageDurationCount"
SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN = "layerAverageFormatPattern"

SETTINGS_KEY_SEND_LAYERINFORMATION_VIA_WEBSOCKET = "sendLayerInformationsViaWebSocket"

SETTINGS_KEY_EXCLUDE_FOLDERS = "excludeFolders"
SETTINGS_KEY_EXCLUDE_FOLDERS_EXPRESSION = "excludeFoldersExpression"

SETTINGS_KEY_PRINTER_DISPLAY_OUTPUT_INTERVAL = "printerDisplayOutputInterval"

SETTINGS_KEY_SHOW_TIME_IN_NAVBAR = "showTimeInNavBar"
SETTINGS_KEY_TIME_IN_NAVBAR_POSITION = "timeInNavBarPosition"

SETTINGS_KEY_PRINTTIMELEFT_WITHOUT_SECONDS = "printTimeLeftWithoutSeconds"

SETTINGS_KEY_LAYERINDICATOR_LOOKAHEAD_LIMIT = "layerIndicatorLookAheadLimit"

SETTINGS_KEY_TOGGLE_DISPLAY_DELAY = "toggleDisplayDelay"

# HEIGHT_METHODE_Z_MAX = "zMax"
# HEIGHT_METHODE_Z_EXTRUSION = "zExtrusion"
# HEIGHT_METHODE_Z_EXPRESSION = "zExpression"

NOT_PRESENT = "-"
LAYER_MESSAGE_PREFIX = "M117 INDICATOR-Layer"
LAYER_COUNT_EXPRESSION = ".*\n?" +LAYER_MESSAGE_PREFIX + "([0-9]+)"

# Match G1 Z149.370 F1000 or G0 F9000 X161.554 Y118.520 Z14.950     ##no comments
# mine: ^[^;](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)
# pr:   ^G[0|1](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)
Z_HEIGHT_EXPRESSION = "^[^;]*G[0|1](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)"
zHeightPattern = re.compile(Z_HEIGHT_EXPRESSION)

# Match G0 or G1 positive extrusion e.g. G1 X58.030 Y72.281 E0.1839 F2250
# EXTRUSION_EXPRESSION = "G[0|1] .*E[+]*([0-9]+[.]*[0-9]*).*"
# extrusionPattern = re.compile(EXTRUSION_EXPRESSION)
# Match feedrate
FEEDRATE_EXPRESSION = "^G[0|1] .*F(\d+\.?\d*).*"
feedratePattern = re.compile(FEEDRATE_EXPRESSION)

# Match Fan speed
FANSPEED_EXPRESSION = "^M106.* S(\d+\.?\d*).*"
fanSpeedPattern = re.compile(FANSPEED_EXPRESSION)
FAN_OFF_EXPRESSION = "^M107.*"
fanOffPattern = re.compile(FAN_OFF_EXPRESSION)

M600_EXPRESSION = "^M600.*"
m600Pattern = re.compile(M600_EXPRESSION)

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
ETA_KEYWORD_EXPRESSION = "[estimated_end_time]"
ETA_CHANGEFILAMENT_KEYWORD_EXPRESSION = "[estimated_changefilament_time]"
CHANGEFILAMENTTIME_LEFT_KEYWORD_EXPRESSION = "[changefilamenttime_left]"
CHANGEFILAMENT_COUNT_KEYWORD_EXPRESSION = "[changefilament_count]"
PRINTER_STATE_KEYWORD_EXPRESSION = "[printer_state]"
M73PROGRESS_KEYWORD_EXPRESSION = "[M73progress]"    # see https://github.com/tpmullan/OctoPrint-DetailedProgress
CURRENT_FILENAME_KEYWORD_EXPRESSION = "[current_print_filename]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/214
CURRENT_BED_TEMP_KEYWORD_EXPRESSION = "[current_bed_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL0_TEMP_KEYWORD_EXPRESSION = "[current_tool0_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL1_TEMP_KEYWORD_EXPRESSION = "[current_tool1_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL2_TEMP_KEYWORD_EXPRESSION = "[current_tool2_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL3_TEMP_KEYWORD_EXPRESSION = "[current_tool3_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL4_TEMP_KEYWORD_EXPRESSION = "[current_tool4_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL5_TEMP_KEYWORD_EXPRESSION = "[current_tool5_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL6_TEMP_KEYWORD_EXPRESSION = "[current_tool6_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210
CURRENT_TOOL7_TEMP_KEYWORD_EXPRESSION = "[current_tool7_temp]"    # see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/210

UPDATE_DISPLAY_REASON_FRONTEND_CALL = "frontEndCall"
UPDATE_DISPLAY_REASON_HEIGHT_CHANGED = "heightChanged"
UPDATE_DISPLAY_REASON_PROGRESS_CHANGED = "progressChanged"
UPDATE_DISPLAY_REASON_LAYER_CHANGED = "layerChanged"
UPDATE_DISPLAY_REASON_FEEDRATE_CHANGED = "feedrateChanged"
UPDATE_DISPLAY_REASON_FANSPEED_CHANGED = "fanspeedChanged"
UPDATE_DISPLAY_REASON_PRINTERSTATE_CHANGED = "printerStateChanged"
UPDATE_DISPLAY_REASON_M73PROGRESS_CHANGED = "m73ProgressChanged"
UPDATE_DISPLAY_REASON_M600_OCCURRED = "m600Occurred"
UPDATE_DISPLAY_REASON_TIMER_TRIGGER = "timerTrigger"

# Same as setup.py 'plugin_identifier'
PLUGIN_KEY_PREFIX = "DisplayLayerProgress_"

MOVEMENT_ABSOLUTE = "g90_abs"
MOVEMENT_RELATIVE = "g91_real"

class LayerDetectorFileProcessor(octoprint.filemanager.util.LineProcessorStream):

    def __init__(self, fileBufferedReader, allLayerExpressions, logger):
        super(LayerDetectorFileProcessor, self).__init__(fileBufferedReader)
        self._allLayerExpressions = allLayerExpressions
        self._logger = logger
        self._currentLayerCount = 0
        self.totalLayerNumbers = 0
        self.selectedLayerExpression = None

    def process_line(self, origLine):
        if not len(origLine):
            return None
        # line = origLine.decode('utf-8') # convert byte -> str
        # line = stringUtils.to_native_str(origLine)
        # print (origLine)
        isBytesLineForPy3 = type(origLine) is bytes and not (type(origLine) is str)
        # if (isBytesLineForPy3):
            # line = origLine.decode('utf8')
            # line = origLine.decode('ISO-8859-1')
            # line = stringUtils.to_unicode(origLine, errors="replace")

        line = stringUtils.to_unicode(origLine, errors="replace")
        line = line.lstrip()

        if (len(line) != 0 and line[0] == ";"):
            if (self.selectedLayerExpression == None):
                for layerExpression in self._allLayerExpressions:
                    inputLine = line
                    line = self._modifyLineIfLayerComment(inputLine, layerExpression)
                    if line is not inputLine:
                        # pattern matched, skip other expressions
                        self.selectedLayerExpression = layerExpression
                        break
                # line = line.encode('utf-8')   # convert str -> byte
            else:
                line = self._modifyLineIfLayerComment(line, self.selectedLayerExpression)
        else:
            line = origLine

        if (isBytesLineForPy3 and type(line) is str):
            # line = line.encode('utf8')
            # line = line.encode('ISO-8859-1')
            line = stringUtils.to_bytes(line, errors="replace")
        else:
            if (isBytesLineForPy3 == False):
                # do nothing, because we don't modify the line
                if (type(line) is unicode):
                    line = stringUtils.to_native_str(line)
        return line

    def _modifyLineIfLayerComment(self, line, layerExpression):
        pattern = layerExpression.expression
        matched = pattern.match(line)
        if matched:
            groupIndex = layerExpression.groupIndex

            if layerExpression.type_countable:
                # just use the layerCounter
                self._currentLayerCount = self._currentLayerCount + 1
                currentLayer = str(self._currentLayerCount)
            else:
                # read layer number from line
                currentLayer = str(matched.group(groupIndex))
            self.totalLayerNumbers = currentLayer
            endline = '\r\n' if line.endswith('\r\n') else '\n'
            line = line + LAYER_MESSAGE_PREFIX + currentLayer + endline

        return line


class DisplaylayerprogressPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
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
    # _tempCurrentHeightFromFile = 0.0
    # _tempCurrentTotalHeight = 0.0
    _layerTotalCountWithoutOffset = NOT_PRESENT
    _currentLayer = NOT_PRESENT
    _progress = str(0)
    _currentHeight = NOT_PRESENT
    _totalHeight = NOT_PRESENT
    # _totalHeightWithExtrusion = NOT_PRESENT # DEPRECATED will be skiped in next release
    # _totalHeightFromExpression = NOT_PRESENT
    _feedrate = NOT_PRESENT
    _feedrateG0 = NOT_PRESENT
    _feedrateG1 = NOT_PRESENT
    _fanSpeed = NOT_PRESENT
    _isPrinterRunning = False
    _layerDurationDeque = None
    _startLayerTime = None
    _currentETA = NOT_PRESENT
    _lastM117Command = None
    _m600LayerList = list()
    _m600LayerProcessingList = list()
    # async processing queues
    _updateDisplayCommandQueue = CommandQueue()
    _sentGCodeHookCommandQueue = CommandQueue()
    _sendingGCodeHookCommandQueue = CommandQueue()

    def __init__(self):
        self._showProgressOnPrinterDisplay = False
        self._showLayerOnPrinterDisplay = False
        self._showHeightOnPrinterDisplay = False
        self._showFeedrateOnPrinterDisplay = False
        self._showFanSpeedOnPrinterDisplay = False
        self._showETAOnPrinterDisplay = False

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
        self._currentHeightFormatted = NOT_PRESENT
        self._totalHeightFormatted = NOT_PRESENT
        # self._totalHeightWithExtrusionFormatted = NOT_PRESENT
        self._currentTemperatures = dict()

        self._filamentChangeTimeLeftInSeconds = 0
        self._filamentChangeTimeLeftFormatted = NOT_PRESENT
        self._filamentChangeETAFormatted = NOT_PRESENT

        self._printerState = ""
        self._lastPrinterState = ""
        self._m73Progress = ""

        self._currentFilename = ""

        self._printTimeGeniusPluginImplementationState = None
        self._printTimeGeniusPluginImplementation = None

        self._busyIndicatorActive = False

        self.stopWatchOn = False
        self.stopWatchValue = 0

        self._updateDisplayTimer = None
        self._currentPrinterDisplayMessagePattern = ""
        # self._settings_debugging_enabled = False
        # self._settings_show_all_printer_messages = True
        # self._settings_eta_format = '%H:%M'
        # self._settings_add_trailingchar = False
        # self._settings_layer_offset = 0
        # self._settings_layer_avarage_duration_count = 5
        # self._settings_layer_avarage_format_pattern = '{H}h:{M:02}m:{S:02}s'
        # self._settings_printerdisplay_messagepattern = ''
        # self._settings_show_on_state = True
        # self._settings_state_messagepattern = ''
        # self._settings_show_on_navbar = True
        # self._settings_navbar_messagepattern = ''
        # self._settings_show_on_browser_title = True
        # self._settings_browser_title_mode = 'overwrite'
        # self._settings_browser_title_messagepattern = '[progress]% [estimated_end_time]'
        # self._settings_show_on_printerdisplay = True
        # self._settings_update_only_while_printing = False
        # self._settings_send_layerinformation_via_websocket = True
        # self._settings_feedrate_factor = '1.0'
        # self._settings_feedrate_format = '{:.2f}'
        # self._settings_height_format = '{:.1f}'
        # self._settings_printerDisplayOutputInterval = 0


    def initialize(self):
        self._initializeEventLogger()

        self._updateDisplayCommandQueue.initCommandQueue(self._updateDisplayWorkerMethod)
        self._sentGCodeHookCommandQueue.initCommandQueue(self.sentGCodeHookWorkerMethod)
        self._sendingGCodeHookCommandQueue.initCommandQueue(self.sendingGCodeHookWorkerMethod)

        self._cachedSettings = CachedSettings(self._settings)
        self._layerDurationDeque = deque(maxlen=self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT))

        # prepare expression-settings
        self._evaluatePrinterMessagePattern()
        self._parseLayerExpressions(self._cachedSettings.getStringValue(SETTINGS_KEY_LAYER_EXPRESSIONS))
        self._layerDetectorFileProcessor = None
        self._layerDetectorFileProcessorLastProcessedFilename = None


    def _initializeEventLogger(self):
        # setup our custom logger
        logPostfix = "events"
        self._event_file_logger = logging.getLogger("octoprint.plugins." + self._settings.plugin_key + "."+logPostfix)

        from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
        event_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix=logPostfix),
                                                                when="D", backupCount=3)
        event_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        event_logging_handler.setLevel(logging.DEBUG)

        # remove all handlers first
        for handler in self._event_file_logger.handlers:
            self._event_file_logger.removeHandler(handler)

        self._event_file_logger.addHandler(event_logging_handler)
        self._event_file_logger.setLevel(logging.DEBUG)
        self._event_file_logger.propagate = False


    ######################################################################################### FILE/GCODE PROCESSOR HOOKS

    # Modified the GCODE -> replace all Layer-Comments with G-Code Message-Comments
    def createFilePreProcessor(self, path, file_object, blinks=None, printer_profile=None, allow_overwrite=True, *args,
                           **kwargs):

        self._layerDetectorFileProcessorLastProcessedFilename = None
        fileName = file_object.filename

        if not octoprint.filemanager.valid_file_type(fileName, type="gcode"):
            return file_object

        addLayerIndicators = self._cachedSettings.getBooleanValue(SETTINGS_KEY_ADD_LAYER_INDICATORS)
        if  addLayerIndicators == False:
            return file_object

        if (hasattr(file_object, "path")):
            path = file_object.path
            alreadyAddedLayerIndicators = self._alreadyAddedLayerIndicators(path)
            if (alreadyAddedLayerIndicators == "property found" or alreadyAddedLayerIndicators == "marker found"):
                return file_object

        # check filesize
        # filePath = file_object.path
        # if (filePath != None):
        #     fileSize = os.path.getsize(filePath)
        #     if fileSize > (50 *1024 *1024):
        #         # send notification to the user, file is to big
        #         # start extra thread for processing
        #         return file_object
        self._logger.info("FilePreProcessor. Checking LayerExpressions.")
        result = self._checkLayerExpressionValid()
        if (result == False):
            self._logger.error("LayerExpressions not valid.")
            return file_object

        self._logger.info("FilePreProcessor. LayerExpression valid. Start processing...")
        fileStream = file_object.stream()

        self._layerDetectorFileProcessor = LayerDetectorFileProcessor(fileStream, self._allLayerExpressions, self._logger)
        self._layerDetectorFileProcessorLastProcessedFilename = file_object

        return octoprint.filemanager.util.StreamWrapper(fileName,
                                                        self._layerDetectorFileProcessor
                                                        )

    # eval current layer from modified g-code (comm.sending_tread, comm._monitor)
    def queuingGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        # needed to handle non utf-8 characters
        # commandAsString = cmd.encode('ascii', 'ignore')
        # commandAsString = octoprint.util.to_native_str(cmd)
        commandAsString = stringUtils.to_native_str(cmd)
        # print("********************** " + commandAsString)
        self._eventLogging("QUEUING-HOOK: " + commandAsString)
        # prevent double messages
        if commandAsString.startswith("M117"):
            if self._lastM117Command == commandAsString:
                # filter double M117 commands
                self._eventLogging("QUEUING-HOOK DROP COMMAND: " + commandAsString)
                return []
            else:
                self._lastM117Command = commandAsString

        # add to queue for async-processing
        self._sendingGCodeHookCommandQueue.addToQueue(commandAsString)

        # layer
        if commandAsString.startswith(LAYER_MESSAGE_PREFIX):
            # filter M117 indicator-command, not needed any more
            return []

        # movement type
        if "G90" == gcode:
            self._movementMode = MOVEMENT_ABSOLUTE
        if "G91" == gcode:
            self._movementMode = MOVEMENT_RELATIVE
        return

    # do the stuff in async-way
    def sendingGCodeHookWorkerMethod(self, commandAsString):
        # layer
        if commandAsString.startswith(LAYER_MESSAGE_PREFIX):

            layerOffset = self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_OFFSET)
            self._currentLayer = str(int(commandAsString[len(LAYER_MESSAGE_PREFIX):]) + layerOffset)

            ## calculate time of layer printing
            layerDuration = 0
            currentTime = datetime.now()
            if self._startLayerTime is not None:
                layerDuration = currentTime - self._startLayerTime

            self._layerDurationDeque.append(layerDuration)
            self._startLayerTime = currentTime

            self._updateDisplay(UPDATE_DISPLAY_REASON_LAYER_CHANGED)
            # filter M117 indicator-command, not needed any more
            return

        # M600
        if (commandAsString.startswith("M600")):
            self._updateDisplay(UPDATE_DISPLAY_REASON_M600_OCCURRED)
            return

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

        if (commandAsString.startswith("M73 P")):
            self._m73Progress = commandAsString.split(" ")[1][1:]
            self._updateDisplay(UPDATE_DISPLAY_REASON_M73PROGRESS_CHANGED)

        pass


    # eval current layer from modified g-code (comm.sending_thread)
    def sentGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        showDesktopPrinterDisplay = self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES)
        if  showDesktopPrinterDisplay == True:
            # needed to handle non utf-8 characters
            # commandAsString = cmd.encode('ascii', 'ignore')
            # commandAsString = octoprint.util.to_native_str(cmd)
            commandAsString = stringUtils.to_native_str(cmd)

            self._eventLogging("SENT-HOOK: " + commandAsString)
            if commandAsString.startswith("M117 "):
                # add to queue for async-processing
                self._sentGCodeHookCommandQueue.addToQueue(commandAsString)
        return

    # do the stuff in async-way
    def sentGCodeHookWorkerMethod(self, commandAsString):
        showDesktopPrinterDisplay = self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES)
        if (showDesktopPrinterDisplay == True):
            printerMessage = commandAsString[len("M117 "):]
            if self._cachedSettings.getBooleanValue(SETTINGS_KEY_ADD_TRAILINGCHAR):
                printerMessage = printerMessage[:-1]

            printerMessage = "&nbsp;" + printerMessage + "&nbsp;"
            # self._plugin_manager.send_plugin_message(self._identifier, dict(showDesktopPrinterDisplay=showDesktopPrinterDisplay,
            #                                                                printerDisplay=printerMessage))
            self._sendDataToClient(dict(
                                        busy=self._busyIndicatorActive,
                                        showDesktopPrinterDisplay=showDesktopPrinterDisplay,
                                        printerDisplay=printerMessage
                                        )
                                    )
        pass


    #################################################################################################### PRIVATE METHODS

    # method reads layer/height informations from selected file
    # def _extractLayerAndHeightInformation(self, line, layerNumberPattern, zMaxPattern):
    def _extractLayerInformation(self, line, layerNumberPattern):
        result = False
        ## Layer evaluation
        matched = layerNumberPattern.match(line)  # identify layer count
        if matched:
            # self._logger.info("Layer indicator found")
            result = True
            # layerOffset = self._settings.get_int([SETTINGS_KEY_LAYER_OFFSET])
            # self._layerTotalCountWithoutOffset = str(int(matched.group(1)) + layerOffset)
            self._layerTotalCountWithoutOffset = int(matched.group(1))
            # self._logger.info("Count '"+self._layerTotalCount+"'")

        # movement type
        # if (line.startswith("G90")):
        #     self._movementMode = MOVEMENT_ABSOLUTE
        #     self._currentRelativeHeight = self._tempCurrentHeightFromFile
        # if (line.startswith("G91")):
        #     self._movementMode = MOVEMENT_RELATIVE


        ## Height evaluation
        # Z_HEIGHT_EXPRESSION = "^[^;]*G[0|1](.*)( Z)([+]*[0-9]+[.]*[0-9]*)(.*)"
        # G1 Z149.370 F1000 or G0 F9000 X161.554 Y118.520 Z14.950     ##no comments
        # matched = zHeightPattern.match(line)
        # if matched:
        #     # don't count on negativ extrusion, see issue #76
        #     # if ("E-" in line) == False:
        #     heightFromFile = float(matched.group(3))
        #     # if (self._movementMode == MOVEMENT_RELATIVE):
        #     #     self._tempCurrentHeightFromFile = self._tempCurrentHeightFromFile + heightFromFile
        #     # else:
        #     self._tempCurrentHeightFromFile = heightFromFile
        #     if self._tempCurrentHeightFromFile  > self._tempCurrentTotalHeight:
        #         self._tempCurrentTotalHeight = self._tempCurrentHeightFromFile
        #
        # matched = extrusionPattern.match(line)
        # if matched:
        #     self._totalHeightWithExtrusion = str(self._tempCurrentHeightFromFile )
        #
        # matched = zMaxPattern.match(line)
        # if matched:
        #     self._totalHeightFromExpression = str(matched.group(1))

        return result

    def _getTotalLayerCountAsString(self):
        if (self._layerTotalCountWithoutOffset == NOT_PRESENT):
            return self._layerTotalCountWithoutOffset

        layerOffset = self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_OFFSET)
        return str(self._layerTotalCountWithoutOffset + layerOffset)

    def _resetCurrentValues(self):

        self._currentLayer = NOT_PRESENT
        self._progress = str(0)
        self._currentETA = NOT_PRESENT
        self._currentHeight = NOT_PRESENT
        self._feedrate = NOT_PRESENT
        self._feedrateG0 = NOT_PRESENT
        self._feedrateG1 = NOT_PRESENT
        self._fanSpeed = NOT_PRESENT

        self._startLayerTime = None
        self._layerDurationDeque = deque(maxlen=self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT))
        self._currentHeightFloat = 0.0

        self._filamentChangeTimeLeftInSeconds = 0
        self._filamentChangeTimeLeftFormatted = NOT_PRESENT
        self._filamentChangeETAFormatted = NOT_PRESENT

        self._movementMode = MOVEMENT_ABSOLUTE

        self._currentFilename = NOT_PRESENT

        self._currentPrinterDisplayMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN)


    def _resetTotalValues(self):
        self._layerTotalCountWithoutOffset = NOT_PRESENT
        self._totalHeight = NOT_PRESENT
        # self._totalHeightWithExtrusion = NOT_PRESENT
        # self._totalHeightFromExpression = NOT_PRESENT

    def _activateBusyIndicator(self):
        # self._plugin_manager.send_plugin_message(self._identifier, dict(busy=True))
        self._busyIndicatorActive = True
        self._sendDataToClient(dict(busy=True))

    def _deactivateBusyIndicator(self):
        # self._plugin_manager.send_plugin_message(self._identifier, dict(busy=True))
        self._busyIndicatorActive = False

    def _disablePrintButton(self):
        # self._plugin_manager.send_plugin_message(self._identifier, dict(disablePrint=True))
        self._sendDataToClient(dict(disablePrint=True))

    def _enablePrintButton(self):
        # self._plugin_manager.send_plugin_message(self._identifier, dict(enablePrint=True))
        self._sendDataToClient(dict(enablePrint=True))

    def _checkLayerExpressionValid(self):
        if self._layerExpressionsValid == False:
            # self._plugin_manager.send_plugin_message(self._identifier,
            #                                          dict(notifyType="error",
            #                                               notifyMessage="DisplayLayerProgressPlugin: LayerExpressions not valid! Check Plugin-Settings."))
            self._sendDataToClient(dict(notifyType="error",
                                        notifyMessage="DisplayLayerProgressPlugin: LayerExpressions not valid! Check Plugin-Settings."))
        return self._layerExpressionsValid

    def _initDesktopPinterDisplay(self):
        # classStyle = "stack-topleft"
        # classStyle = "stack-topright"
        # classStyle = "stack-bottomleft"
        # classStyle = "stack-bottomright"
        classStyle = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION_CLASS)
        stackDefinition = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION)

        showDesktopPrinterDisplay = self._cachedSettings.getStringValue(SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES)
        initDesktopDisplay =  showDesktopPrinterDisplay
        # start-workaround https://github.com/foosel/OctoPrint/issues/3400
        # import time
        # time.sleep(2)
        # end-workaround

        self._sendDataToClient(dict(initPrinterDisplay=initDesktopDisplay,
                                    printerDisplayScreenLocation=stackDefinition,
                                    printerDisplayWidth=self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_WIDTH),
                                    classDefinition=classStyle
                                    )
                              )
        pass

    def _executeUpdateDisplayTimer(self):

        self._readTemperatures()
        # Toggle PrinterDisplay
        if (self._cachedSettings.getBooleanValue(SETTINGS_KEY_PRINTERDISPLAY_TOGGLE_ENABLED)):
            if (self._currentPrinterDisplayMessagePattern == self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN)):
                self._currentPrinterDisplayMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN_SECOND)
            else:
                self._currentPrinterDisplayMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN)

        self._updateDisplay(UPDATE_DISPLAY_REASON_TIMER_TRIGGER)


    def _readTemperatures(self):

        self._currentTemperatures = dict()

        temperaturesRead = self._printer.get_current_temperatures()
        # identify how many tools do we have
        printer_profile = self._printer_profile_manager.get_current_or_default()
        printerProfileToolCount = printer_profile['extruder']['count']

        # for toolIndex, filamentLength in enumerate(self.metaDataFilamentLengths):
        for toolIndex in range(printerProfileToolCount):
           toolName = 'tool'+str(toolIndex)
           if toolName in temperaturesRead:
               toolValues = temperaturesRead[toolName]
               self._currentTemperatures[toolName] = toolValues
           pass
        if "bed" in temperaturesRead:
            bedValues = temperaturesRead["bed"]
            self._currentTemperatures["bed"] = bedValues

        pass

    def _updateDisplayWorkerMethod(self, updateReason):
        # self._updateDisplayCommandQueue.addToQueue(updateReason)
        self._updateDisplay(updateReason)
        pass

    def _updateDisplay(self, updateReason):

        startUpdateDisplayTime = octoprint.util.monotonic_time()

        self._eventLogging("UPDATE DISPLAY: " + updateReason)

        currentData = self._printer.get_current_data()

        # NOT NEEDED at the moment estPrintTime = currentData["job"]["estimatedPrintTime"]
        self._printTimeLeft = NOT_PRESENT
        self._printTimeLeftInSeconds = currentData["progress"]["printTimeLeft"]
        if self._printTimeLeftInSeconds is not None:
            self._printTimeLeft = stringUtils.secondsToText(self._printTimeLeftInSeconds, hideSeconds=self._cachedSettings.getBooleanValue(SETTINGS_KEY_PRINTTIMELEFT_WITHOUT_SECONDS))

            # current_time = datetime.today()
            # finish_time = current_time + timedelta(0,self._printTimeLeftInSeconds)
            # self._currentETA = format_time(finish_time, format="short")
            timeFormat = self._cachedSettings.getStringValue(SETTINGS_KEY_ETA_FORMAT)
            self._currentETA  = time.strftime(timeFormat, time.localtime(time.time() + self._printTimeLeftInSeconds))  #hijacked from displalayer-plugin
            pass
        else:
            self._printTimeLeftInSeconds = NOT_PRESENT
            self._currentETA = NOT_PRESENT

        ## formate height values
        self._currentHeightFormatted = self._formatHeightValue(self._currentHeight)
        self._totalHeightFormatted = self._formatHeightValue(self._totalHeight)
        # self._totalHeightWithExtrusionFormatted = self._formatHeightValue(self._totalHeightWithExtrusion)

        # if not self._currentHeightFormatted == NOT_PRESENT:
        #     self._currentHeightFormatted += "mm"
        # if not self._totalHeightFormatted == NOT_PRESENT:
        #     self._totalHeightFormatted += "mm"


        ## calculate feedrate
        feedrate = self._calculateFeedrate(self._feedrate)
        feedrateG0 = self._calculateFeedrate(self._feedrateG0)
        feedrateG1 = self._calculateFeedrate(self._feedrateG1)

        ## calculate layer duration
        self._lastLayerDuration = "-"
        self._lastLayerDurationInSeconds = "-"
        self._averageLayerDuration = "-"
        self._averageLayerDurationInSeconds = "-"

        # calculate layer durations
        if len(self._layerDurationDeque) > 0:
            lastLayerDurationTimeDelta = self._layerDurationDeque[-1]
            if isinstance( lastLayerDurationTimeDelta, int):
                self._lastLayerDurationInSeconds = lastLayerDurationTimeDelta
            else:
                self._lastLayerDurationInSeconds = lastLayerDurationTimeDelta.seconds
            self._lastLayerDuration = stringUtils.strfdelta(lastLayerDurationTimeDelta, self._cachedSettings.getStringValue(SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN))

            # avarag calc only if we have engough layer measurments
            allLayerDurationCount = len(self._layerDurationDeque)
            if allLayerDurationCount == self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT):
                calcAverageDuration = 0
                allLayerDurations = list(self._layerDurationDeque)

                for duration in allLayerDurations:
                    if type(duration) is timedelta:
                        calcAverageDuration = calcAverageDuration + duration.total_seconds()

                calcAverageDuration = calcAverageDuration / allLayerDurationCount
                calcAverageDurationTimeDelta = timedelta(seconds = calcAverageDuration)
                self._averageLayerDuration = stringUtils.strfdelta(calcAverageDurationTimeDelta, self._cachedSettings.getStringValue(SETTINGS_KEY_LAYER_AVARAGE_FORMAT_PATTERN))
                self._averageLayerDurationInSeconds = calcAverageDurationTimeDelta.seconds

        # layerChanged event, then calculate the predicted filamentChange time
        if (updateReason == UPDATE_DISPLAY_REASON_LAYER_CHANGED):   #TODO only if it is included into message output pattern in settings-ui
            currenLayerNumber = int(self._currentLayer)

            if (len(self._m600LayerProcessingList) > 0):
                self._nextM600Layer = self._m600LayerProcessingList[0]

                if (self._nextM600Layer == currenLayerNumber):
                    self._m600LayerProcessingList.pop(0)
                    self._nextM600Layer == 0
            else:
                self._nextM600Layer = 0

            layerDiff = self._nextM600Layer - currenLayerNumber
            # Only calculate the M600 time if the layer one is already printed
            if (layerDiff >= 0 and self._lastLayerDurationInSeconds > 0 and currenLayerNumber > 1):
                layerDuration = self._lastLayerDurationInSeconds
                # for a better precision, take avarage layerDuration and not the last one
                if (type(self._averageLayerDurationInSeconds) == int and int(self._averageLayerDurationInSeconds) > 0):
                    layerDuration = self._averageLayerDurationInSeconds

                self._filamentChangeTimeLeftInSeconds = layerDuration * layerDiff
                self._filamentChangeTimeLeftFormatted = stringUtils.secondsToText(self._filamentChangeTimeLeftInSeconds)
                timeFormat = self._cachedSettings.getStringValue(SETTINGS_KEY_ETA_FORMAT)
                self._filamentChangeETAFormatted = time.strftime(timeFormat, time.localtime(time.time() + self._filamentChangeTimeLeftInSeconds))

        currentBedTemperature = ""
        if ("bed" in self._currentTemperatures):
            currentBedTemperature = str(self._currentTemperatures["bed"]["actual"])

        currentTool0Temperature = ""
        currentTool1Temperature = ""
        currentTool2Temperature = ""
        currentTool3Temperature = ""
        currentTool4Temperature = ""
        currentTool5Temperature = ""
        currentTool6Temperature = ""
        currentTool7Temperature = ""

        if ("tool0" in self._currentTemperatures):
            currentTool0Temperature = str(self._currentTemperatures["tool0"]["actual"])
        if ("tool1" in self._currentTemperatures):
            currentTool1Temperature = str(self._currentTemperatures["tool1"]["actual"])
        if ("tool2" in self._currentTemperatures):
            currentTool2Temperature = str(self._currentTemperatures["tool2"]["actual"])
        if ("tool3" in self._currentTemperatures):
            currentTool3Temperature = str(self._currentTemperatures["tool3"]["actual"])
        if ("tool4" in self._currentTemperatures):
            currentTool4Temperature = str(self._currentTemperatures["tool4"]["actual"])
        if ("tool5" in self._currentTemperatures):
            currentTool5Temperature = str(self._currentTemperatures["tool5"]["actual"])
        if ("tool6" in self._currentTemperatures):
            currentTool6Temperature = str(self._currentTemperatures["tool6"]["actual"])
        if ("tool7" in self._currentTemperatures):
            currentTool7Temperature = str(self._currentTemperatures["tool7"]["actual"])


        currentValueDict = {
            PROGRESS_KEYWORD_EXPRESSION: self._progress,
            CURRENT_LAYER_KEYWORD_EXPRESSION: self._currentLayer,
            TOTAL_LAYER_KEYWORD_EXPRESSION: self._getTotalLayerCountAsString(),
            # CURRENT_HEIGHT_KEYWORD_EXPRESSION: self._currentHeight,
            CURRENT_HEIGHT_KEYWORD_EXPRESSION: self._currentHeightFormatted,
            # TOTAL_HEIGHT_KEYWORD_EXPRESSION: self._totalHeight,
            TOTAL_HEIGHT_KEYWORD_EXPRESSION: self._totalHeightFormatted,
            FEEDRATE_KEYWORD_EXPRESSION: feedrate,
            FEEDRATE_G0_KEYWORD_EXPRESSION: feedrateG0,
            FEEDRATE_G1_KEYWORD_EXPRESSION: feedrateG1,
            FANSPEED_KEYWORD_EXPRESSION: self._fanSpeed,
            PRINTTIME_LEFT_EXPRESSION: self._printTimeLeft,
            LAYER_LAST_DURATION_EXPRESSION: self._lastLayerDuration,
            LAYER_AVERAGE_DURATION_EXPRESSION: self._averageLayerDuration,
            ETA_KEYWORD_EXPRESSION: self._currentETA,
            ETA_CHANGEFILAMENT_KEYWORD_EXPRESSION: self._filamentChangeETAFormatted,
            CHANGEFILAMENTTIME_LEFT_KEYWORD_EXPRESSION: self._filamentChangeTimeLeftFormatted,
            CHANGEFILAMENT_COUNT_KEYWORD_EXPRESSION: str(len(self._m600LayerProcessingList)),
            PRINTER_STATE_KEYWORD_EXPRESSION: self._printerState,
            M73PROGRESS_KEYWORD_EXPRESSION: self._m73Progress,
            CURRENT_FILENAME_KEYWORD_EXPRESSION: self._currentFilename,
            CURRENT_BED_TEMP_KEYWORD_EXPRESSION: currentBedTemperature,
            CURRENT_TOOL0_TEMP_KEYWORD_EXPRESSION: currentTool0Temperature,
            CURRENT_TOOL1_TEMP_KEYWORD_EXPRESSION: currentTool1Temperature,
            CURRENT_TOOL2_TEMP_KEYWORD_EXPRESSION: currentTool2Temperature,
            CURRENT_TOOL3_TEMP_KEYWORD_EXPRESSION: currentTool3Temperature,
            CURRENT_TOOL4_TEMP_KEYWORD_EXPRESSION: currentTool4Temperature,
            CURRENT_TOOL5_TEMP_KEYWORD_EXPRESSION: currentTool5Temperature,
            CURRENT_TOOL6_TEMP_KEYWORD_EXPRESSION: currentTool6Temperature,
            CURRENT_TOOL7_TEMP_KEYWORD_EXPRESSION: currentTool7Temperature
        }
        # printerMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN)
        printerMessagePattern = self._currentPrinterDisplayMessagePattern
        printerMessageCommand = "M117 " + stringUtils.multiple_replace(printerMessagePattern, currentValueDict)


        ############ prepare clientMessage
        clientMessageDict = dict()

        clientMessageDict.update({'busy': self._busyIndicatorActive})

        if self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ON_STATE):
            stateMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_STATE_MESSAGEPATTERN)
            stateMessage = stringUtils.multiple_replace(stateMessagePattern, currentValueDict)
            clientMessageDict.update( {'stateMessage' : stateMessage } )

        if self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ON_NAVBAR):
            navBarMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_NAVBAR_MESSAGEPATTERN)
            navBarMessage = stringUtils.multiple_replace(navBarMessagePattern, currentValueDict)
            clientMessageDict.update( {'navBarMessage' : navBarMessage } )

        if self._cachedSettings.getStringValue(SETTINGS_KEY_SHOW_ON_BROWSER_TITLE):
            browserTitleMode = self._cachedSettings.getStringValue(SETTINGS_KEY_BROWSER_TITLE_MODE)

            browserTitleMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_BROWSER_TITLE_MESSAGEPATTERN)
            browserTitleMessage = stringUtils.multiple_replace(browserTitleMessagePattern, currentValueDict)

            browserTitleDict = dict(
                browserTitleMode = browserTitleMode,
                message = browserTitleMessage
            )
            clientMessageDict.update({'browserTitle': browserTitleDict})

        # the stateMessage-format is fixed
        # stateMessage = self._currentLayer + " / " + self._layerTotalCount
        # clientMessageDict.update({'stateMessage': stateMessage})

        # the heightMessage-format is fixed
        # heightMessage = self._currentHeight + " / " + self._totalHeight
        # heightMessage = self._currentHeightFormatted + " / " + self._totalHeightFormatted
        # if not self._totalHeight == NOT_PRESENT:
        #     heightMessage += "mm"
        # clientMessageDict.update({'heightMessage': heightMessage})

        # showHeightInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_HEIGHT_IN_STATSUBAR])
        # clientMessageDict.update({'showHeightInStatusBar': showHeightInStatusBar})
        # showLayerInStatusBar = self._settings.get_boolean([SETTINGS_KEY_SHOW_LAYER_IN_STATSUBAR])
        # clientMessageDict.update({'showLayerInStatusBar': showLayerInStatusBar})

        showDesktopPrinterDisplay = self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ALL_PRINTERMESSAGES)
        clientMessageDict.update({'showDesktopPrinterDisplay': showDesktopPrinterDisplay})

        # prepare Printer
        if self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_ON_PRINTERDISPLAY):
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
            elif updateReason == UPDATE_DISPLAY_REASON_TIMER_TRIGGER:
                shouldSendToPrinter = True

            if self._cachedSettings.getBooleanValue(SETTINGS_KEY_UPDATE_ONLY_WHILE_PRINTING):
                if self._isPrinterRunning:
                    #if self._printer.is_printing():
                    shouldSendToPrinter = True
                else:
                    shouldSendToPrinter = False

            if shouldSendToPrinter == True:
                ######################################################################################## SEND TO PRINTER
                self._sendCommandToPrinter(printerMessageCommand)

        ############################################################ SEND TO BROWSER (stateBar, navBar and browserTitle)
        # self._plugin_manager.send_plugin_message(self._identifier, dict(clientMessageDict))
        self._sendDataToClient(dict(clientMessageDict))

        ##################################################### FIRE EVENT, so that other Plugins could react on the event

        eventPayload = dict(
            updateReason=updateReason,
            totalLayer=self._getTotalLayerCountAsString(),
            currentLayer=self._currentLayer,
            lastLayerDuration=self._lastLayerDuration,
            lastLayerDurationInSeconds=self._lastLayerDurationInSeconds,
            averageLayerDuration=self._averageLayerDuration,
            averageLayerDurationInSeconds=self._averageLayerDurationInSeconds,
            currentHeight=self._currentHeight,
            currentHeightFormatted=self._currentHeightFormatted,
            totalHeight=self._totalHeight,
            totalHeightFormatted=self._totalHeightFormatted,
            # totalHeightWithExtrusion=self._totalHeightWithExtrusion,
            # totalHeightWithExtrusionFormatted=self._totalHeightWithExtrusionFormatted,
            feedrate=self._feedrate,
            feedrateG0=self._feedrateG0,
            feedrateG1=self._feedrateG1,
            fanspeed=self._fanSpeed,
            progress=self._progress,
            m73progress=self._m73Progress,
            printTimeLeft=self._printTimeLeft,
            printTimeLeftInSeconds=self._printTimeLeftInSeconds,
            printerState=self._printerState,
            estimatedEndTime=self._currentETA,
            estimatedChangedFilamentTime=self._filamentChangeETAFormatted,
            changeFilamentTimeLeft=self._filamentChangeTimeLeftFormatted,
            changeFilamentTimeLeftInSeconds=self._filamentChangeTimeLeftInSeconds,
            changeFilamentCount=len(self._m600LayerProcessingList),
            currentFilename=self._currentFilename
        )

        if (self._lastSendEventBusData != eventPayload):
            if updateReason is not UPDATE_DISPLAY_REASON_FRONTEND_CALL:
                eventKey = PLUGIN_KEY_PREFIX + updateReason
                eventManager().fire(eventKey, eventPayload)

            ##################################################### WEBSOCKET
            if self._cachedSettings.getBooleanValue(SETTINGS_KEY_SEND_LAYERINFORMATION_VIA_WEBSOCKET):
                self._plugin_manager.send_plugin_message(self._identifier + "-websocket-payload", eventPayload)
                pass

            self._lastSendEventBusData = eventPayload
        else:
            self._eventLogging("SEND-EVENTBUS: not send, because duplicated dict:" + str(eventPayload))

        endUpdateDisplayTime = octoprint.util.monotonic_time()
        updateDisplateDuration = endUpdateDisplayTime - startUpdateDisplayTime
        if (self.stopWatchOn == True):
            self.stopWatchValue =  self.stopWatchValue +  updateDisplateDuration

        pass

    _lastSendEventBusData = dict()


    def _calculateFeedrate(self, feedrate):
        if feedrate == "-":
            return feedrate
        feedrateFactor = self._cachedSettings.getStringValue(SETTINGS_KEY_FEEDRATE_FACTOR)
        feedrateFormat = self._cachedSettings.getStringValue(SETTINGS_KEY_FEEDRATE_FORMAT)

        newFeedrate = float(feedrateFactor) * float(feedrate)
        result = feedrateFormat.format(newFeedrate)
        return result

    def _formatHeightValue(self, heightValue):
        result = heightValue
        heightFormat = "unknown"
        heightValueAsFloat = None
        try:
            heightValueAsFloat = float(heightValue)
        except Exception:
            return result

        try:
            heightFormat = self._cachedSettings.getStringValue(SETTINGS_KEY_HEIGHT_FORMAT)
            result = heightFormat.format(heightValueAsFloat)
        except (Exception) as error:
            errorMessage = "ERROR during format '" + heightFormat + "' height value '" + str(heightValueAsFloat) + "'. Message: '" + str(error) + "'"
            self._logger.error(errorMessage)
            self._eventLogging(errorMessage)
        return result

    _lastSendPrinterCommand = None
    _lastSendTime = None
    # printer specific command-manipulation.
    # e.g. ANET E10 cuts the last char from M117-commands, so this helper adds an additional underscore to the message
    def _sendCommandToPrinter(self, command):
        if (self._lastSendPrinterCommand != command):

            # is intervall output enabled
            intervalCount = self._cachedSettings.getIntValue(SETTINGS_KEY_PRINTER_DISPLAY_OUTPUT_INTERVAL)
            if (intervalCount > 0):
                if (self._lastSendTime != None):
                    currentTime = octoprint.util.monotonic_time()
                    currentInterval = currentTime - self._lastSendTime
                    if (currentInterval < intervalCount):
                        return

            if self._cachedSettings.getStringValue(SETTINGS_KEY_ADD_TRAILINGCHAR):
                if command.startswith("M117"):
                    command += "_"
            # logging for debugging print("Send GCode:" + command)
            self._eventLogging("SEND-COMMAND: "+command)
            self._printer.commands(command)
            self._lastSendPrinterCommand = command
            self._lastSendTime = octoprint.util.monotonic_time()
        else:
            self._eventLogging("SEND-PRINTER: not send, because duplicated command:" + command)

    _lastSendClientData = dict()
    # sends the data-dictonary to the client/browser
    def _sendDataToClient(self, dataDict):
        if (self._lastSendClientData != dataDict):
            self._plugin_manager.send_plugin_message(self._identifier, dataDict)
            self._lastSendClientData = dataDict
        else:
            self._eventLogging("SEND-CLIENT: not send, because duplicated dict:" + str(dataDict))

    def _evaluatePrinterMessagePattern(self):
        printerMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN)

        self._showProgressOnPrinterDisplay = False
        self._showLayerOnPrinterDisplay = False
        self._showHeightOnPrinterDisplay = False
        self._showFeedrateOnPrinterDisplay = False
        self._showFanSpeedOnPrinterDisplay = False

        if (printerMessagePattern != None and len(printerMessagePattern) > 0):
            if PROGRESS_KEYWORD_EXPRESSION in printerMessagePattern:
                self._showProgressOnPrinterDisplay = True

            if CURRENT_LAYER_KEYWORD_EXPRESSION in printerMessagePattern \
                    or TOTAL_LAYER_KEYWORD_EXPRESSION in printerMessagePattern:
                self._showLayerOnPrinterDisplay = True
            if CURRENT_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern \
                    or TOTAL_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern:
                self._showHeightOnPrinterDisplay = True
            if FEEDRATE_KEYWORD_EXPRESSION in printerMessagePattern \
                    or FEEDRATE_G0_KEYWORD_EXPRESSION in printerMessagePattern \
                    or FEEDRATE_G1_KEYWORD_EXPRESSION in printerMessagePattern:
                self._showFeedrateOnPrinterDisplay = True
            if FANSPEED_KEYWORD_EXPRESSION in printerMessagePattern:
                self._showFanSpeedOnPrinterDisplay = True

        if (self._cachedSettings.getBooleanValue(SETTINGS_KEY_PRINTERDISPLAY_TOGGLE_ENABLED)):
            printerMessagePattern = self._cachedSettings.getStringValue(SETTINGS_KEY_PRINTERDISPLAY_MESSAGEPATTERN_SECOND)
            # copy and paste
            if (printerMessagePattern != None and len(printerMessagePattern) > 0):
                if PROGRESS_KEYWORD_EXPRESSION in printerMessagePattern:
                    self._showProgressOnPrinterDisplay = True

                if CURRENT_LAYER_KEYWORD_EXPRESSION in printerMessagePattern \
                        or TOTAL_LAYER_KEYWORD_EXPRESSION in printerMessagePattern:
                    self._showLayerOnPrinterDisplay = True
                if CURRENT_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern \
                        or TOTAL_HEIGHT_KEYWORD_EXPRESSION in printerMessagePattern:
                    self._showHeightOnPrinterDisplay = True
                if FEEDRATE_KEYWORD_EXPRESSION in printerMessagePattern \
                        or FEEDRATE_G0_KEYWORD_EXPRESSION in printerMessagePattern \
                        or FEEDRATE_G1_KEYWORD_EXPRESSION in printerMessagePattern:
                    self._showFeedrateOnPrinterDisplay = True
                if FANSPEED_KEYWORD_EXPRESSION in printerMessagePattern:
                    self._showFanSpeedOnPrinterDisplay = True


    def _parseLayerExpressions(self, layerExpressionPatterns):
        result = None
        self._layerExpressionsValid = False
        if layerExpressionPatterns  is not None and len(layerExpressionPatterns ) != 0:
            self._allLayerExpressions = []
            #patterns = "1		[;LAYER:([0-9]+).*]		CURA\r\n" + "1		[; layer ([0-9]+),.*]	Simplify3D\r\n" + "count	[BEGIN_LAYER_OBJECT]	KISSlicer"
            lines = layerExpressionPatterns.split("\n")
            lineIndex = 0
            try:
                for line in lines:
                    if (len(line.strip()) == 0):
                        continue
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

    layerIndicatorProcessedFileMarker = "; DisplayLayerProgress_layerIndicatorProcessed = true"

    # Looks for a property at the end of the file that this file was already processed with LayerIndicators
    # If not present loop thru the first lines looking for M117 LayerIndicator messages
    # returning
    # - no marker
    # - property found
    # - marker found
    def _alreadyAddedLayerIndicators(self, path):
        resultType = "no marker"
        try:
            lastLines = stringUtils.getLastLinesFromFile(path, 10)
            for line in lastLines:
                if (line.startswith(self.layerIndicatorProcessedFileMarker)):
                    resultType = "property found"
                    break

            if resultType == "no marker":
                # lets look in the first 500 (adjustable) lines, maybe there is already an M117 Indicator
                lineCounter = 0
                # layerIndicatorLookAheadLimit = 500
                layerIndicatorLookAheadLimit = self._cachedSettings.getStringValue(SETTINGS_KEY_LAYERINDICATOR_LOOKAHEAD_LIMIT)
                with open(path) as fileHandle:
                    for line in fileHandle:
                        lineCounter = lineCounter + 1
                        # reached the limit
                        if (lineCounter > layerIndicatorLookAheadLimit):
                            self._logger.info("Limit of " + str(layerIndicatorLookAheadLimit) + " reached and no " + LAYER_MESSAGE_PREFIX + " found")
                            break
                        # found an indicator
                        if (line.startswith(LAYER_MESSAGE_PREFIX)):
                            resultType = "marker found"
                            break

        except Exception as error:
            errorMessage = "ERROR! File: '" + path + "' could not read check-marking'"
            self._logger.exception(errorMessage)
            self._eventLogging(errorMessage)
        return resultType

    # Add at the end of the file a property to indicate the this file was alread processed
    def _markFileLayerIndicatorProcessed(self, path):
        try:
            fileHandle = open(path, "a+")
            fileHandle.write("; BEGIN DISPLAYLAYERPROGRESS SETTINGS\n")
            fileHandle.write(self.layerIndicatorProcessedFileMarker+"\n")
            fileHandle.write("; END   DISPLAYLAYERPROGRESS SETTINGS\n")
            fileHandle.close()
        except Exception as error:
            errorMessage = "ERROR! File: '" + path + "' could not be open for check-marking'"
            self._logger.exception(errorMessage)
            self._eventLogging(errorMessage)

        pass

    def _eventLogging(self, logMessage):
        if EVENT_LOGGING_ENABLED or self._cachedSettings.getBooleanValue(SETTINGS_KEY_DEBUGGING_ENABLED):
            threadName = threading.current_thread().name
            threadId = str(threading.current_thread().ident)
            threadPattern = "["+threadId + "::" + threadName + "]"
            self._event_file_logger.debug(logMessage + " " + threadPattern)

    # get the plugin with status information
    # [0] == status-string
    # [1] == implementaiton of the plugin
    def _getPluginInformation(self, pluginKey):

        status = None
        implementation = None

        if pluginKey in self._plugin_manager.plugins:
            plugin = self._plugin_manager.plugins[pluginKey]
            if plugin != None:
                if (plugin.enabled == True):
                    status = "enabled"
                    # for OP 1.4.x we need to check agains "icompatible"-attribute
                    if (hasattr(plugin, 'incompatible')):
                        if (plugin.incompatible == False):
                            implementation = plugin.implementation
                        else:
                            status = "incompatible"
                    else:
                        # OP 1.3.x
                        implementation = plugin.implementation
                    pass
                else:
                    status = "disabled"
        else:
            status = "missing"

        return [status, implementation]

    ######################################################################################################### PUBLIC API

    @octoprint.plugin.BlueprintPlugin.route("/values", methods=["GET"])
    def get_displayLayerProgressValues(self):

        # return data via the default API endpoint
        return flask.jsonify({
            "layer": {
                "total": self._getTotalLayerCountAsString(),
                "current": self._currentLayer,
                "averageLayerDuration": self._averageLayerDuration,
                "averageLayerDurationInSeconds": self._averageLayerDurationInSeconds,
                "lastLayerDuration": self._lastLayerDuration,
                "lastLayerDurationInSeconds": self._lastLayerDurationInSeconds
            },
            "height": {
                "total": self._totalHeight,
                "current": self._currentHeight,
                "totalFormatted": self._totalHeightFormatted,
                "currentFormatted": self._currentHeightFormatted
            },
            "fanSpeed": self._fanSpeed,
            "feedrate": self._feedrate,
            "feedrateG0": self._feedrateG0,
            "feedrateG1": self._feedrateG1,
            "print": {
                "printerState": self._printerState,
                "progress": self._progress,
                "m73progress": self._m73Progress,
                "timeLeft": self._printTimeLeft,
                "timeLeftInSeconds": self._printTimeLeftInSeconds,
                "estimatedEndTime": self._currentETA,
                "estimatedChangedFilamentTime": self._filamentChangeETAFormatted,
                "changeFilamentTimeLeft": self._filamentChangeTimeLeftFormatted,
                "changeFilamentTimeLeftInSeconds": self._filamentChangeTimeLeftInSeconds,
                "changeFilamentCount": len(self._m600LayerProcessingList)
            },
            "currentFilename": self._currentFilename
        })

    ################################################################################################ COMMON PLUGIN HOOKS

    # start up the system
    def on_after_startup(self):
        # check if needed plugins were available
        # make sure that my layer preprocessor is always the last processor
        preProcessorHooksOrderedDic = self._file_manager._preprocessor_hooks
        preProcessorHooksOrderedDic[self._identifier] = __plugin_implementation__.createFilePreProcessor

        pluginInfo = self._getPluginInformation("PrintTimeGenius")
        self._printTimeGeniusPluginImplementationState = pluginInfo[0]
        self._printTimeGeniusPluginImplementation = pluginInfo[1]


        self._resetCurrentValues()
        self._startUpdateDisplayToggleTimer()

    def on_shutdown(self):
        self._stopUpdateDisplayTimer()

    def _startUpdateDisplayToggleTimer(self):
        if (self._updateDisplayTimer != None):
            self._updateDisplayTimer.cancel()

        self._updateDisplayTimer = RepeatedTimer(self._cachedSettings.getIntValue(SETTINGS_KEY_TOGGLE_DISPLAY_DELAY),
                                                 self._executeUpdateDisplayTimer, run_first=True)
        self._updateDisplayTimer.start()

    def _stopUpdateDisplayTimer(self):
        if (self._updateDisplayTimer != None):
            self._updateDisplayTimer.cancel()

    # progress-hook (called in new Thread)
    def on_print_progress(self, storage, path, progress):
        currentData = self._printer.get_current_data()
        useSystemProgress = True
        newProgress = 0
        if ("progress" in currentData):
            progressDict =  currentData["progress"]

            if (self._printTimeGeniusPluginImplementationState == "enabled"):
                useSystemProgress = False
            else:
                useSystemProgress = True

            if (useSystemProgress == False):
                printTime =  float(progressDict["printTime"] if progressDict["printTime"] != None else 0.0)
                printTimeLeft =  float(progressDict["printTimeLeft"] if progressDict["printTimeLeft"] != None else 0.0)
                endTime = (printTime + printTimeLeft)
                if (endTime > 0):
                    newProgress = round(printTime / endTime * 100.0)

        # progress 0 - 100
        if (useSystemProgress == True):
            self._progress = str(progress)
        else:
            # take calculted progress of PrintTimeGenius
            self._progress = str(int(newProgress))

        self._eventLogging("ON_PRINT_PROGRESS: " + self._progress)
        # logging for debugging self._logger.info("**** print_progress: '" + self._progress + "'")
        # self._updateDisplay(UPDATE_DISPLAY_REASON_PROGRESS_CHANGED)
        self._updateDisplayCommandQueue.addToQueue(UPDATE_DISPLAY_REASON_PROGRESS_CHANGED)

    # start/stop event-hook
    def on_event(self, event, payload):
        self._eventLogging("EVENT: " + event)

        if event == Events.METADATA_ANALYSIS_FINISHED:
            # after the fileProcessor is done a METADATA_ANALYSIS_FINISHED event is fired

            if (self._layerDetectorFileProcessor != None):
                fileLocation = payload.get("origin")
                selectedFilename = payload.get("path")

                self._storeLayerCountInMeta(fileLocation, selectedFilename, self._layerDetectorFileProcessor.totalLayerNumbers)
                self._readHeightFromFileMeta(fileLocation, selectedFilename)

                self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.FILE_ADDED:
            fileLocation = payload.get("storage")
            # addedFilename = payload.get("name")
            addedFilename = payload.get("path")
            if (self._layerDetectorFileProcessorLastProcessedFilename != None):
                self._layerDetectorFileProcessorLastProcessedFilename = None
                if (fileLocation == octoprint.filemanager.FileDestinations.LOCAL):
                    addedFile = self._file_manager.path_on_disk(fileLocation, addedFilename)
                    # mark this file that LayerIndicators were added
                    self._markFileLayerIndicatorProcessed(addedFile)
                else:
                    pass #skipping sd-card files

        elif event == Events.FILE_SELECTED:
            self._initializeEventLogger()
            fileLocation = payload.get("origin")
            selectedFilename = payload.get("path")
            selectedFile = "SD-CARD FILE NOT SUPPORTED"

            if (fileLocation == octoprint.filemanager.FileDestinations.LOCAL):
                selectedFile = self._file_manager.path_on_disk(fileLocation, selectedFilename)

            self._logger.info("File '" + selectedFile + "' selected. Determining number of layers.")
            self._resetCurrentValues()
            self._resetTotalValues()

            self._currentFilename = selectedFilename

            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            if (fileLocation == octoprint.filemanager.FileDestinations.SDCARD):
                errorMessage = "Files on SDCard not supported for layer analyse"
                self._logger.error(errorMessage)
                self._eventLogging(errorMessage)
                return

            skipLayerDetection = False

            # is it an excluded file that should not be analysed?
            if (self._cachedSettings.getBooleanValue(SETTINGS_KEY_EXCLUDE_FOLDERS) == True):
                excludedFoldersExpression = self._cachedSettings.getStringValue(SETTINGS_KEY_EXCLUDE_FOLDERS_EXPRESSION)
                excludedFilenamePattern = re.compile(excludedFoldersExpression)
                matched = excludedFilenamePattern.match(selectedFilename)
                if (matched):
                    self._logger.info("File '" + selectedFile + "' is excluded from layer analyse.")
                    skipLayerDetection = True

            if (skipLayerDetection == False):
                markerLayerCount = LAYER_COUNT_EXPRESSION
                layerNumberPattern = re.compile(markerLayerCount)

                # zMaxPattern = re.compile(self._settings.get([SETTINGS_KEY_ZMAX_EXPRESSION_PATTERN]))

                # self._tempCurrentHeightFromFile = 0.0
                # self._tempCurrentTotalHeight = 0.0
                self._nextM600Layer = 0
                self._m600LayerList = list()
                self._m600LayerProcessingList = list()

                self._filamentChangeTimeLeftInSeconds = 0
                self._filamentChangeTimeLeftFormatted = NOT_PRESENT
                self._filamentChangeETAFormatted = NOT_PRESENT

                lineNumber = 0
                self._activateBusyIndicator()

                # check FileMeta for totalHeight
                self._readHeightFromFileMeta(fileLocation, selectedFilename)

                layerIndicatorAlreadyFound = False

                try:
                    currentLayerNumber = 0
                    # added ISO, see https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/126
                    # import sys
                    # if (sys.version[0] == '2'):
                    import io
                    with io.open(selectedFile, "r", encoding="ISO-8859-1") as f:
                        for line in f:
                            lineNumber += 1
                            # layerIndicatorFound = self._extractLayerAndHeightInformation(line, layerNumberPattern, zMaxPattern)
                            layerIndicatorFound = self._extractLayerInformation(line, layerNumberPattern)

                            if (layerIndicatorFound == True and layerIndicatorAlreadyFound == False):
                                layerIndicatorAlreadyFound = True
                                logMessage = "First LayerIndicator found in line '"+str(lineNumber)+"'"
                                #self._logger.info(logMessage)
                                self._eventLogging(logMessage)

                            if (layerIndicatorFound == True):
                                currentLayerNumber = self._layerTotalCountWithoutOffset
                            else:
                                # check for M600 filament change
                                matched = m600Pattern.match(line)  # identify layer count
                                if matched:
                                    # filemant change detected
                                    layerOffset = self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_OFFSET)
                                    self._m600LayerList.append(currentLayerNumber + layerOffset)

                    if (layerIndicatorAlreadyFound == False):
                        logMessage = "No LayerIndicator found!!!"
                        self._logger.warn(logMessage)
                        self._eventLogging(logMessage)
                        # inform user (if enabled)
                        showMissingLayerIndicatorWarning = self._cachedSettings.getBooleanValue(SETTINGS_KEY_SHOW_MISSING_LAYER_INDICATOR_WARNING)
                        if (showMissingLayerIndicatorWarning == True):
                            self._sendDataToClient(dict(notifyType="warning", notifyMessage="Layer indicator not found in file: '"+selectedFilename+"'<br>Check 'layer pattern', 'Look ahead limit' in DisplayLayerProgress-Settings and reUpload the file!"))
                    else:
                        # store totalLayerCount
                        self._storeLayerCountInMeta(fileLocation, selectedFilename, self._layerTotalCountWithoutOffset)

                        # New check if file is already marked with property
                        resultType = self._alreadyAddedLayerIndicators(selectedFile)
                        if (resultType == "marker found"):
                            # add property to confirm that the file already marked
                            self._markFileLayerIndicatorProcessed(selectedFile)

                except Exception as error:
                    errorMessage = "ERROR! File: '" + selectedFile + "' Line: " + str(lineNumber) + " Message: '" + str(error) + "'"
                    self._logger.exception(errorMessage)
                    self._eventLogging(errorMessage)

                self._deactivateBusyIndicator()
                # Height values are evaluated. Depending on the ZMode, assign value to final totalHeight-Variable
                # if self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_MAX:
                #     self._totalHeight = str("%.2f" % self._tempCurrentTotalHeight)
                # elif self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_EXTRUSION:
                #     if not self._totalHeightWithExtrusion == NOT_PRESENT:
                #         self._totalHeight = str("%.2f" % float(self._totalHeightWithExtrusion))
                #     else:
                #         self._totalHeight = NOT_PRESENT
                # elif self._settings.get([SETTINGS_KEY_TOTAL_HEIGHT_METHODE]) == HEIGHT_METHODE_Z_EXPRESSION:
                #     if not self._totalHeightFromExpression == NOT_PRESENT:
                #         self._totalHeight = str("%.2f" % float(self._totalHeightFromExpression))
                #     else:
                #         self._totalHeight = NOT_PRESENT

                self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            self._logger.info("File select-event processing done!'")

        elif event == Events.FILE_DESELECTED or \
             event == Events.DISCONNECTING:
            self._resetCurrentValues()
            self._resetTotalValues()
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.PRINT_STARTED:

            self.stopWatchOn = True
            self.stopWatchValue = 0

            self._initializeEventLogger()
            self._isPrinterRunning = True
            self._logger.info("Printing started. Detailed progress started." + str(payload))

            self._updateDisplayCommandQueue.printJobStarted()
            self._sentGCodeHookCommandQueue.printJobStarted()
            self._sendingGCodeHookCommandQueue.printJobStarted()

            self._resetCurrentValues()
            # which M600 layers should be processed
            self._m600LayerProcessingList = list(self._m600LayerList)

            self._currentFilename = payload.get("path")

            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)
            self._checkLayerExpressionValid()

        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):

            self.stopWatchOn = False
            # print("##################################### " + str(self.stopWatchValue))
            self.stopWatchValue = 0

            self._logger.info("Printing stopped. Detailed progress stopped.")

            self._updateDisplayCommandQueue.printJobStopped()
            self._sentGCodeHookCommandQueue.printJobStopped()
            self._sendingGCodeHookCommandQueue.printJobStopped()

            self._progress = str(0)
            # send to navbar
            self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

            self._eventLogging("event print done!")
            # not needed could be done via standard code-settings self._sendCommandToPrinter("M117 Print Done")
            self._isPrinterRunning = False

        elif event == Events.CLIENT_OPENED or event == Events.SETTINGS_UPDATED:
            self._initDesktopPinterDisplay()
            self._updateDisplayCommandQueue.addToQueue(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

        elif event == Events.PRINTER_STATE_CHANGED:
            currentPrinterStateId = payload['state_id']
            # eavluate printer_state
            if (currentPrinterStateId != None):
                if (currentPrinterStateId == "PRINTING"):
                    printerState = "printing"
                elif (currentPrinterStateId == "OPERATIONAL"):
                    printerState = "operational"
                elif (currentPrinterStateId == "OFFLINE"):
                    printerState = "offline"
                elif (currentPrinterStateId == "PAUSED"):
                    printerState = "paused"
                elif (currentPrinterStateId == "ERROR" or currentPrinterStateId == "CLOSED_WITH_ERROR"):
                    printerState = "error"
                else:
                    printerState = "idle"

                if (self._lastPrinterState != printerState):
                    self._lastPrinterState = printerState
                    self._printerState = printerState
                    self._updateDisplay(UPDATE_DISPLAY_REASON_PRINTERSTATE_CHANGED)

        self._eventLogging("EVENT processed::" + event)


    # these values could be loaded via JavaScript
    def _storeLayerCountInMeta(self, fileLocation, selectedFilename, layerTotalCountWithoutOffset):
        self._logger.info("Store layer count in MetaFile")
        myMetaData = {
            "totalLayerCountWithoutOffset": str(layerTotalCountWithoutOffset)
        }
        self._file_manager.set_additional_metadata(fileLocation, selectedFilename, self._plugin_info.key,
                                                   myMetaData,
                                                   overwrite=True)

        # self._sendDataToClient(dict(action="reloadFileView"))

    def _readHeightFromFileMeta(self, fileLocation, selectedFilename):

        # read only for currently selected filename and not for future files (upload during running print)
        if (self._currentFilename == selectedFilename):
            self._logger.info("Read total height from MetaFile")
            metaDataDict = self._file_manager.get_metadata(fileLocation, selectedFilename)
        else:
            self._logger.info("Did NOT reading total height from MetaFile, because analyse was done for not selected file. Current: '"+self._currentFilename+"' Analyse for: '"+selectedFilename+"'")
            return

        if (metaDataDict == None):
            self._logger.info("MetaData not present for: '"+selectedFilename+"'. Could not read height")
            return

        # - read height from meta
        if ("analysis" in metaDataDict):
            analysisDict = metaDataDict["analysis"]
            if ("dimensions" in analysisDict):
                dimensionsDict = analysisDict["dimensions"]
                self._totalHeight = str(dimensionsDict["height"])
            # if ("printingArea" in analysisDict):
            #     printingAreaDict = analysisDict["printingArea"]
            #     self._totalHeight = str(printingAreaDict["maxZ"])
        if (self._totalHeight == None or self._totalHeight == NOT_PRESENT):
            self._logger.info("Total height not found in MetaFile")
        else:
            self._logger.debug("Total height read from MetaFile " + str(self._totalHeight))

        # # - read total layer from meta
        # if (self._plugin_info.key in metaDataDict):
        #     pluginMetaDict = metaDataDict[self._plugin_info.key]
        #     if ("totalLayerCountWithoutOffset" in pluginMetaDict):
        #         self._layerTotalCountWithoutOffset = int(pluginMetaDict["totalLayerCountWithoutOffset"])
        #         layerFound = True
        # return layerFound

    # save current settings do some input validation
    def on_settings_save(self, data):
        # !!! data includes only the delta settings between the last save-action !!!

        layerExpressions = data.get(SETTINGS_KEY_LAYER_EXPRESSIONS)
        if layerExpressions is not None:
            result = self._parseLayerExpressions(layerExpressions)
            if result is not None:
                # self._plugin_manager.send_plugin_message(self._identifier, dict(notifyType="error", notifyMessage = result))
                self._sendDataToClient(dict(notifyType="error", notifyMessage = result))

        initDesktopPrinterDisplay = False
        printerDisplayScreenLocationDefinition = data.get(SETTINGS_KEY_PRINTERDISPLAY_SCREENLOCATION)
        if printerDisplayScreenLocationDefinition is not None:
            try:
                json.loads("{"+printerDisplayScreenLocationDefinition+"}")
                initDesktopPrinterDisplay = True
            except:
                # self._plugin_manager.send_plugin_message(self._identifier, dict(notifyType="error", notifyMessage="Printer ScreenLocation could not parsed!"))
                self._sendDataToClient(dict(notifyType="error", notifyMessage="Printer ScreenLocation could not parsed!"))

        printerDisplayWidthDefinition = data.get(SETTINGS_KEY_PRINTERDISPLAY_WIDTH)
        if printerDisplayWidthDefinition is not None:
            initDesktopPrinterDisplay = True

        # default save function
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        # Refresh cached settings
        self._cachedSettings.updateSettings(self._settings)

        self._evaluatePrinterMessagePattern()
        self._layerDurationDeque = deque(maxlen=self._cachedSettings.getIntValue(SETTINGS_KEY_LAYER_AVARAGE_DURATION_COUNT))

        self._resetCurrentValues()
        self._startUpdateDisplayToggleTimer()

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
                self._cachedSettings.updateSettings(self._settings)

                return flask.jsonify(self.get_settings_defaults())

        # default/other action
        self._updateDisplay(UPDATE_DISPLAY_REASON_FRONTEND_CALL)

    # ~~ TemplatePlugin mixin
    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True, name="DisplayLayerProgress")
        ]

    # ~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            installed_version=self._plugin_version,
            showOnState=True,
            showOnNavBar=True,
            showOnPrinterDisplay=True,
            showOnBrowserTitle=True,
            showOnFileListView=True,
            browserTitleMode="overwrite",
            appendActualBedTempBrowserTitle=False,
            appendTargetBedTempBrowserTitle=False,
            addLayerIndicators=True,
            showMissingLayerIndicatorWarning=True,
            showAllPrinterMessages=True,
            stateMessagePattern=
                                "<span title='Might be inaccurate!'>Current Height</span>: <strong id='state_height_message'>[current_height] / [total_height]mm</strong>\n" +
                                "<i class='fa fa-spinner fa-spin dlp-state-busyIndicator' style='display:none'></i>\n" +
                                "<br>\n" +
                                "<span title='Shows the layer information'>Layer</span>: <strong id='state_layer_message'>[current_layer] / [total_layers]</strong>\n" +
                                "<i class='fa fa-spinner fa-spin dlp-state-busyIndicator' style='display:none'></i>\n" +
                                "<br>\n" +
                                "",
            navBarMessagePattern="Progress: <span style='display: inline-block;width:24px;'>[progress]%</span>\n"
                                 "Layer: <span style='display: inline-block;width:24px;'>[current_layer]</span> of\n"
                                 "<span style='display: inline-block;width:24px;'>[total_layers]</span>\n"
                                 "Height: <span style='display: inline-block;width:42px;'>[current_height]</span> of\n"
                                 "<span style='display: inline-block;width:42px;'>[total_height]</span>mm",
#                                 "Feedrate: [feedrate] G0: [feedrate_g0] G1: [feedrate_g1]",
            printerDisplayMessagePattern="[progress]% L=[current_layer]/[total_layers]",
            browserTitleMessagePattern="[progress]% [estimated_end_time] ([printer_state])",
            layerOffset=0,
            addTrailingChar=False,
            # totalHeightMethode=HEIGHT_METHODE_Z_MAX,
            layerExpressions="1\t\t[;\s*LAYER:\s*([0-9]+).*]\t\tCURA\r\n" +
                             "1\t\t[; layer ([0-9]+),.*]\t\tSimplify3D\r\n" +
                             "1\t\t[;LAYER:([0-9]+).*]\t\tideaMaker\r\n" +
                             "count\t[; BEGIN_LAYER_OBJECT.*]\t\tKISSlicer\r\n" +
                             "count\t[;BEFORE_LAYER_CHANGE]\t\tSlic3r\r\n" +
                             "count\t[;LAYER_CHANGE]\t\tPrusa",
            # showLayerInStatusBar=True,
            # showHeightInStatusBar=True,
            updatePrinterDisplayWhilePrinting=False,
            printerDisplayScreenLocation="\"dir1\": \"up\", \"dir2\": \"right\", \"firstpos1\": 40, \"firstpos2\": 10, \"spacing1\": 0, \"spacing2\": 0",
            printerDisplayScreenLocationClass="stack-bottomleft",
            printerDisplayWidth="15%",
            heightFormat="{:.1f}",
            etaFormat="%H:%M",
            feedrateFactor="1.0",
            feedrateFormat="{:.2f}",
            debuggingEnabled=False,
            layerAverageDurationCount=5,
            layerAverageFormatPattern="{H}h:{M:02}m:{S:02}s",
            # zMaxExpressionPattern=";MAXZ:([0-9]+[.]*[0-9]*).*",
            sendLayerInformationsViaWebSocket=True,
            excludeFolders = False,
            excludeFoldersExpression = "",
            printerDisplayOutputInterval = 0,
            timeInNavBarPosition = "right",
            showTimeInNavBar = False,
            currentTimeFormat = "HH:mm",
            printTimeLeftWithoutSeconds = True,
            layerIndicatorLookAheadLimit = 750,
            togglePrinterDisplayEnabled = False,
            toggleDisplayDelay = 3,
            secondPrinterDisplayMessagePattern = "H=[current_height]/[total_height]"
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

                stable_branch=dict(
                    name="Only Release",
                    branch="master",
                    comittish=["master"]
                ),
                prerelease_branches=[
                    dict(
                        name="Release & Candidate",
                        branch="pre-release",
                        comittish=["pre-release", "master"],
                    ),
                    dict(
                        name="Release & Candidate & in development",
                        branch="development",
                        comittish=["development", "pre-release", "master"],
                    )
                ],

                # update method: pip
                #pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/{target_version}.zip"
                # pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/latest/download/master.zip"
                pip="https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/download/{target_version}/master.zip"
            )
        )


## START: baustelle
    def sanitize_temperatures(self, comm, parsed_temps):
        # self.currentToolTemp = parsed_temps["T0"][0]
        # self.currentToolTemp = parsed_temps["B"][0]
        return dict((k, v) for k, v in parsed_temps.items()
                    if isinstance(v, tuple) and len(v) == 2 and self.is_sane(v[0]))

    def is_sane(self, actual):
        return 1.0 <= actual <= 300.0

    def gcode_script_variables(self, comm, script_type, script_name, *args, **kwargs):
        if not script_type == "gcode" or not script_name == "beforePrintStarted":
            return None

        prefix = None
        postfix = None
        variables = dict(myvariable="Hi! I'm a variable!")
        return prefix, postfix, variables
## END: baustelle

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "DisplayLayerProgress Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = DisplaylayerprogressPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        # https://docs.octoprint.org/en/master/plugins/hooks.html#octoprint-comm-protocol-gcode-phase
        #"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.queuingGCodeHook,
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.queuingGCodeHook,
        # "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.sendingGCodeHook,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sentGCodeHook,
        # "octoprint.filemanager.preprocessor": __plugin_implementation__.createFilePreProcessor
# baustelle        "octoprint.comm.protocol.temperatures.received": __plugin_implementation__.sanitize_temperatures,
# baustelle        "octoprint.comm.protocol.scripts": __plugin_implementation__.gcode_script_variables
    }


#
path = "/Users/o0632/Library/Application Support/OctoPrint/uploads/3DBenchy.gcode"
# path = "/Users/o0632/Library/Application Support/OctoPrint/uploads/LeftAnchorBlock_0.2mm_ABS_MK3SMMU2S_12h19m.gcode"
filename = "3DBenchy.gcode"
#
# plugin = DisplaylayerprogressPlugin()
# result = plugin._alreadyAddedLayerIndicators(path, filename)
# print(result)
# print(plugin._markFileLayerIndicatorProcessed("",path, filename))


# printTimeLeftInSeconds = 4000
# #
# # from time import strftime
# # from time import gmtime
# #
# # print(strftime("%Hh:%Mm:%Ss", gmtime(printTimeLeftInSeconds)))
#
# print(stringUtils.secondsToText(printTimeLeftInSeconds, hideSeconds=True))
