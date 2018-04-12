# coding=utf-8
from __future__ import absolute_import

import octoprint.filemanager
import octoprint.filemanager.util
import octoprint.plugin
import octoprint.util
import re
from octoprint.events import Events

## CONSTs
NOT_PRESENT = "NOT-PRESENT"
LAYER_MESSAGE_PREFIX = "M117 INDICATOR-Layer"
LAYER_EXPRESSION = ";LAYER:([0-9]*)"
LAYER_COUNT_EXPRESSION = ";LAYER_COUNT:([0-9]*)"

class LayerDetectorFileProcessor(octoprint.filemanager.util.LineProcessorStream):
	def process_line(self, line):
		markerLayer = LAYER_EXPRESSION
		pattern = re.compile(markerLayer)

		matched = pattern.match(line)
		if matched:
			currentLayer = matched.group(1)
			line = LAYER_MESSAGE_PREFIX + currentLayer + "\r\n"

		# line = strip_comment(line).strip() DO NOT USE, because total-layer count disapears
		if not len(line):
			return None
		return line

class DisplaylayerprogressPlugin(octoprint.plugin.SettingsPlugin,
								 octoprint.plugin.AssetPlugin,
								 octoprint.plugin.TemplatePlugin,
								 # my stuff
								 octoprint.plugin.EventHandlerPlugin,
								 octoprint.plugin.ProgressPlugin,
								 ):
	## VAR
	_layerTotalCount = NOT_PRESENT
	_currentLayer = NOT_PRESENT
	_progress = str(0)

	## Modififed the GCODE -> replace all Layer-Comments with G-Code Message-Comments
	def myPreProcessor(self, path, file_object, blinks=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
		if not octoprint.filemanager.valid_file_type(path, type="gcode"):
			return file_object

		import os
		name, _ = os.path.splitext(file_object.filename)

		return octoprint.filemanager.util.StreamWrapper(file_object.filename, LayerDetectorFileProcessor(file_object.stream()))

	## eval current layer from modified g-code
	def myGCodeHook(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		commandAsString = str(cmd)
		if commandAsString.startswith(LAYER_MESSAGE_PREFIX):
			self._logger.info("**** g-code hook: '" + commandAsString + "'")
			self._currentLayer = str(int(commandAsString[len(LAYER_MESSAGE_PREFIX):]) + 1)
			## filter M117 command, not needed any more
			self.updateDisplay()
			return []
		return

	## progress-hook
	def on_print_progress(self, storage, path, progress):
		# progress 0 - 100
		self._progress = str(progress)
		self._logger.info("**** print_progress: '" + storage + "' '" + path + "' '" + self._progress + "'")
		self.updateDisplay()

	def updateDisplay(self):
		progressMessageCommand = ""
		progressMessageNavBar = ""
		if self._layerTotalCount == NOT_PRESENT:
			# show only the percentage
			progressMessageCommand = "M117 " + self._progress + "% "
			progressMessageNavBar = "Layer: - / -"  # "Progress: " + self._progress + "% "

		elif self._currentLayer == NOT_PRESENT:
			# show only the percentage
			progressMessageCommand = "M117 " + self._progress + "% "
			progressMessageNavBar = "Layer: 0 / " + self._layerTotalCount  # "Progress: " + self._progress + "% "

		else:
			progressMessageCommand = "M117 " + self._progress + "% " + self._currentLayer + "/" + self._layerTotalCount + "_"
			progressMessageNavBar = "Layer: " + self._currentLayer + " / " + self._layerTotalCount  # "Progress: " + self._progress + "%  "

		print("###################################################################################")
		print(progressMessageCommand)
		print("###################################################################################")

		# Send to PRINTER
		self._printer.commands(progressMessageCommand)
		# Send to NAVBAR
		self._plugin_manager.send_plugin_message(self._identifier, dict(progressMessage=progressMessageNavBar))
		self._logger.error(progressMessageNavBar)

	## start/stop event-hook
	def on_event(self, event, payload):
		#		self._logger.error("**** EVENT:" + event)
		#		self._logger.error("**** EVENT-PAYLOAD:" + str(payload))

		if event == Events.FILE_SELECTED:
			self._logger.info("File selected. Detailed progress started.")

			selectedFile = payload.get("file", "")
			selectedFileName = payload.get("filename", "")
			#			self._logger.info("selectedFile::::" + selectedFile)
			#			self._logger.info("selectedFileName::::" + selectedFileName)
			markerLayerCount = LAYER_COUNT_EXPRESSION
			pattern = re.compile(markerLayerCount)

			line_found = False
			lineNumber = 0;
			with open(selectedFile, "r") as f:
				for line in f:
					lineNumber = lineNumber + 1
					# self._logger.info("line:"+line)
					matched = pattern.match(line)
					if matched:
						self._layerTotalCount = str(matched.group(1))
			self.updateDisplay()

		elif event == Events.PRINT_STARTED:
			self._logger.info("PRINTING STARTED::::" + str(payload))
			self.updateDisplay()
		elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
			self._logger.info("Printing stopped. Detailed progress stopped.")

			# self._layerTotalCount = NOT_PRESENT
			# self._currentLayer = NOT_PRESENT
			# send to the printer
			self._printer.commands("M117 Print Done")
			# send to navbar
			self.updateDisplay()

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
		)

	##~~ AssetPlugin mixin
	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/DisplayLayerProgress.js"],
			css=["css/DisplayLayerProgress.css"],
			less=["less/DisplayLayerProgress.less"]
		)

	##~~ Softwareupdate hook
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
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.myGCodeHook,
		"octoprint.filemanager.preprocessor": __plugin_implementation__.myPreProcessor
	}
