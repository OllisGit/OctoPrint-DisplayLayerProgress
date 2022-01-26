/*
 * View model for DisplayLayerProgress
 *
 * Author: Olli
 * License: AGPLv3
 */
$(function () {
    function DisplaylayerprogressViewModel(parameters) {
        var PLUGIN_ID = "DisplayLayerProgress";
        // enable support of resetSettings
        new ResetSettingsUtil().assignResetSettingsFeature(PLUGIN_ID, function(data){
                                // assign new settings-values // TODO find a more generic way
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.addLayerIndicators(data.addLayerIndicators);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showMissingLayerIndicatorWarning(data.showMissingLayerIndicatorWarning);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnState(data.showOnState);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnNavBar(data.showOnNavBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnPrinterDisplay(data.showOnPrinterDisplay);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnBrowserTitle(data.showOnBrowserTitle);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnFileListView(data.showOnFileListView);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showAllPrinterMessages(data.showAllPrinterMessages);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.stateMessagePattern(data.stateMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.navBarMessagePattern(data.navBarMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayMessagePattern(data.printerDisplayMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.browserTitleMessagePattern(data.browserTitleMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.browserTitleMode(data.browserTitleMode);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.appendActualBedTempBrowserTitle(data.appendActualBedTempBrowserTitle);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.appendTargetBedTempBrowserTitle(data.appendTargetBedTempBrowserTitle);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayScreenLocation(data.printerDisplayScreenLocation);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayWidth(data.printerDisplayWidth);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.addTrailingChar(data.addTrailingChar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerExpressions(data.layerExpressions);
//                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showLayerInStatusBar(data.showLayerInStatusBar);
//                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showHeightInStatusBar(data.showHeightInStatusBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.updatePrinterDisplayWhilePrinting(data.updatePrinterDisplayWhilePrinting);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.heightFormat(data.heightFormat);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.etaFormat(data.etaFormat);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.feedrateFactor(data.feedrateFactor);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.feedrateFormat(data.feedrateFormat);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.debuggingEnabled(data.debuggingEnabled);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerAverageDurationCount(data.layerAverageDurationCount);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerAverageFormatPattern(data.layerAverageFormatPattern);
//                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.zMaxExpressionPattern(data.zMaxExpressionPattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.sendLayerInformationsViaWebSocket(data.sendLayerInformationsViaWebSocket);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.excludeFolders(data.excludeFolders);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.excludeFoldersExpression(data.excludeFoldersExpression);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showTimeInNavBar(data.showTimeInNavBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayScreenLocationClass(data.printerDisplayScreenLocationClass);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.timeInNavBarPosition(data.timeInNavBarPosition);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.currentTimeFormat(data.currentTimeFormat);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printTimeLeftWithoutSeconds(data.printTimeLeftWithoutSeconds);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerIndicatorLookAheadLimit(data.layerIndicatorLookAheadLimit);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.togglePrinterDisplayEnabled(data.togglePrinterDisplayEnabled);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.toggleDisplayDelay(data.toggleDisplayDelay);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.secondPrinterDisplayMessagePattern(data.secondPrinterDisplayMessagePattern);
        });

        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];
        self.temperatureModel = parameters[2];
        self.filesViewModel = parameters[3];
        self.printerStateViewModel = parameters[4];

        self.temperatureModel.bedTemp.actual.subscribe(function(newValue){
            self.updateBedTemperatureInBrowserTitle();
        });

        self.temperatureModel.bedTemp.target.subscribe(function(newValue){
            self.updateBedTemperatureInBrowserTitle();
        });
        self.updateBedTemperatureInBrowserTitle = function(){
            var temperatureText = ""
            var doUpdate = false;
            if (self.settingsViewModel.settings.plugins.DisplayLayerProgress.appendActualBedTempBrowserTitle() == true){
                temperatureText = Math.round(self.temperatureModel.bedTemp.actual()) + "°C";
                doUpdate = true;
            }

            if (self.settingsViewModel.settings.plugins.DisplayLayerProgress.appendTargetBedTempBrowserTitle() == true){
                if (self.settingsViewModel.settings.plugins.DisplayLayerProgress.appendActualBedTempBrowserTitle() == true){
                    temperatureText = temperatureText + "/"+ Math.round(self.temperatureModel.bedTemp.target()) + "°C";
                } else {
                    temperatureText = temperatureText + Math.round(self.temperatureModel.bedTemp.target()) + "°C";
                }
                doUpdate = true;
            }

            if (doUpdate == true && self.temperatureModel.hasBed() == true){
                var currentTitle = document.title;
                if (currentTitle.endsWith("°C")){
                    var spaceIndex = currentTitle.lastIndexOf(' ');
                    if (spaceIndex != -1){
                        currentTitle = currentTitle.substring(0, spaceIndex);
                    } else {
                        currentTitle = "";
                    }
                }
                currentTitle = currentTitle + " " + temperatureText;
                document.title = currentTitle.trim();
            }
        }

        self.stateMessage = ko.observable();
        self.navBarMessage = ko.observable();
        self.defaultBrowserTitleMessage = "";


        self.filesViewModel.getLayerInformation = function(fileItem){
            if (fileItem.DisplayLayerProgress != null){
                return parseInt(fileItem.DisplayLayerProgress.totalLayerCountWithoutOffset) + parseInt(self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerOffset());
            }
            return "-"
        }

        // startup
        self.onStartup = function () {
//            console(self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerOffset());
            // get orig file-item html and add "Layers:"
            $("#files_template_machinecode").text(function(){
                var origFileListHtml = $(this).text();
                var patchedFileItemHtml = origFileListHtml.replace('formatSize(size)"></span></div>', 'formatSize(size)"></span></div>' +
                                        '<div class="size" data-bind="visible: ($root.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnFileListView() == true)" >Layers: <span data-bind="text: $root.getLayerInformation($data)"></span></div>');
                return patchedFileItemHtml;
            });

            var element = $("#state").find(".accordion-inner .progress");
            if (element.length) {
                element.before("<span id='dlp-stateOutputMessage'></span>");

                self.stateMessage.subscribe(function(newValue){
                    $("#dlp-stateOutputMessage").html(newValue);
                });

//                // call backend for update navbar and printer-display
                OctoPrint.get("api/plugin/"+PLUGIN_ID);
            }

            $("#layerExpressionTextArea").numberedtextarea();
        };

        self.onAllBound = function() {
            self.defaultBrowserTitleMessage = document.title;
            self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnBrowserTitle.subscribe(function(newValue){
                if (newValue == false){
                    document.title = self.defaultBrowserTitleMessage
                }
            });

            self.settingsViewModel.settings.plugins.DisplayLayerProgress.showAllPrinterMessages.subscribe(function(newValue){
                if (printerDisplay != null){
                    if (newValue == true){
                        printerDisplay.open();
                    } else {
                        printerDisplay.remove();
                    }

                }
            });

            self.updateClock = function() {
                var clockVisible = self.settingsViewModel.settings.plugins.DisplayLayerProgress.showTimeInNavBar();
                if (clockVisible) {
                    // start and show Clock
                    var position = self.settingsViewModel.settings.plugins.DisplayLayerProgress.timeInNavBarPosition();

                    var clockElement = null;
                    if ("left" == position)
                        clockElement = $("#dlpNavBarTime-left");
                    else {
                        clockElement = $("#dlpNavBarTime-right");
                    }
                    // start clock
                    clockElement.show();
                    var dt = new Date();
                    var dateTimeAsString = moment(dt).format(self.settingsViewModel.settings.plugins.DisplayLayerProgress.currentTimeFormat());
                    clockElement.html( dateTimeAsString );
                    window.setTimeout(self.updateClock, 1000);
                } else {
                    // hide clock and stop clock
                    $("#dlpNavBarTime-left").hide();
                    $("#dlpNavBarTime-right").hide();
                }
            };

            self.settingsViewModel.settings.plugins.DisplayLayerProgress.showTimeInNavBar.subscribe(function(newValue){
                    self.updateClock();
            });
            self.settingsViewModel.settings.plugins.DisplayLayerProgress.timeInNavBarPosition.subscribe(function(newValue){
                    $("#dlpNavBarTime-left").hide();
                    $("#dlpNavBarTime-right").hide();
                    self.updateClock();
            });

            // Start/Show (if needed) clock after inital load
            self.updateClock();

//            self.origGetAdditionDataFunction = self.filesViewModel.getAdditionalData;
//            self.filesViewModel.getAdditionalData = function(data){
//                var additionDataAsHtml = "Layers: 123<br>" + self.origGetAdditionDataFunction(data);
//                console.info("hallo");
//                return additionDataAsHtml;
//            }
        }


        var printerDisplay = null;



        // receive data from server
        self.onDataUpdaterPluginMessage = function (plugin, data) {

            if (plugin != PLUGIN_ID) {
                return;
            }

            if ("reloadFileView" == data.action){
                self.filesViewModel.requestData({force: true});
                return;
            }

            if (data.disablePrint){
                $("#job_print").attr("disabled", "disabled");
                return
            }
            if (data.enablePrint){
                if (self.printerStateViewModel.enablePrint() == true){
                    $("#job_print").removeAttr("disabled");
                }
                return
            }

            if ("busy" in data){
                if (data.busy == true) {
                    $(".dlp-state-busyIndicator").show();
                } else {
                    $(".dlp-state-busyIndicator").hide();
                    if (self.printerStateViewModel.enablePrint() == true){
                        $("#job_print").removeAttr("disabled");
                    }
                }
            } else {
                $(".dlp-state-busyIndicator").hide();
                if (self.printerStateViewModel.enablePrint() == true){
                    $("#job_print").removeAttr("disabled");
                }
            }

            // State
            if (data.stateMessage){
                self.stateMessage(data.stateMessage);
            }

            // NavBar
            if (data.navBarMessage){
                self.navBarMessage(data.navBarMessage);
            }

            // BrowserTitle
            if (data.browserTitle){
                if (data.browserTitle.browserTitleMode == "overwrite"){
                    document.title = data.browserTitle.message;
                } else {
                    document.title = self.defaultBrowserTitleMessage + " " + data.browserTitle.message;
                }
            }

			// Printer Display
            if ( (printerDisplay == null && data.initPrinterDisplay) ||
                  data.initPrinterDisplay){

                var lastTextMessage = null;
                if (printerDisplay != null){
                    // before creating a new PrinterDisplay store the last message
                    lastTextMessage = printerDisplay.text_container[0].innerHTML;
                    $("h4.ui-pnotify-title:contains('Printer Display')").parent().parent().remove();
                }
                //var stack_bar_bottom = {"dir1": "up", "dir2": "left", "spacing1": 0, "spacing2": 0};
                var stack_bar_bottom = JSON.parse("{"+data.printerDisplayScreenLocation+"}");
                printerDisplay = new PNotify({
                    title: 'Printer Display',
                    type: 'info',
                    width: data.printerDisplayWidth,
                    //addclass: "stack-bottomleft",
                    addclass: data.classDefinition,
                    stack: stack_bar_bottom,
                    hide: false
                    });

                if (lastTextMessage != null){
                    printerDisplay.update({
                        text: lastTextMessage
                    });
                }
            }
			if (data.showDesktopPrinterDisplay && data.printerDisplay && printerDisplay != null){
                printerDisplay.update({
                    text: '<h3 class="fontsforweb_fontid_507"><font color="lightblue" style="background-color:blue;">'+data.printerDisplay+'</font></h3>'
                });
			}

			// NotificationMessages
			if (data.notifyType){
			    var notfiyType = data.notifyType;
			    var notifyMessage = data.notifyMessage;
                new PNotify({
                    title: 'Attention',
                    text: notifyMessage,
                    type: notfiyType,
                    hide: false
                    });

			}

        };

        self.onBeforeBinding = function () {
            self.settings = self.settingsViewModel.settings.plugins.DisplayLayerProgress;
            // From server-settings to client-settings
        };

        self.onSettingsBeforeSave = function () {
        }
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: DisplaylayerprogressViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["loginStateViewModel", "settingsViewModel", "temperatureViewModel", "filesViewModel", "printerStateViewModel"],
        // Elements to bind to, e.g. #settings_plugin_DisplayLayerProgress, #tab_plugin_DisplayLayerProgress, ...
        //elements: [document.getElementById("progressinfo_plugin_navbar")]
        elements: [
            document.getElementById("displayLayerProgress_plugin_navbar"),
            document.getElementById("displayLayerProgress_plugin_settings")
        ]
    });
});
