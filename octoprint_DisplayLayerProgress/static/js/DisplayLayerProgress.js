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
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnState(data.showOnState);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnNavBar(data.showOnNavBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnPrinterDisplay(data.showOnPrinterDisplay);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnBrowserTitle(data.showOnBrowserTitle);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showAllPrinterMessages(data.showAllPrinterMessages);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.stateMessagePattern(data.stateMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.navBarMessagePattern(data.navBarMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayMessagePattern(data.printerDisplayMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.browserTitleMessagePattern(data.browserTitleMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.browserTitleMode(data.browserTitleMode);
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
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.zMaxExpressionPattern(data.zMaxExpressionPattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.sendLayerInformationsViaWebSocket(data.sendLayerInformationsViaWebSocket);
        });

        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];

        self.stateMessage = ko.observable();
        self.navBarMessage = ko.observable();
        self.defaultBrowserTitleMessage = "";

        // startup
        self.onStartup = function () {
            //alert("hallo");
            var element = $("#state").find(".accordion-inner .progress");
            if (element.length) {
                element.before("<span id='dlp-stateOutputMessage'></span>");

                self.stateMessage.subscribe(function(newValue){
                    $("#dlp-stateOutputMessage").html(newValue);
                });

//                var busyIndicator = " <i class='fa fa-spinner fa-spin busyIndicator' style='display:none'></i>";
//
//                // height
//                var label = gettext("Current Height");
//                var tooltip = gettext("Might be inaccurate!");
//                element.before("<span id='heightStateOutput' style='display:none'><span title='" + tooltip + "'>" + label + "</span>" + ": "
//                    + "<strong id='state_height_message'>- / -</strong>"+busyIndicator+"  <br/></span>");
//                // layer
//                label = gettext("Layer");
//                tooltip = gettext("Shows the layer information");
//                element.before("<span id='layerStateOutput' style='display:none'> <span title='" + tooltip + "'>" + label + "</span>" + ": "
//                    + "<strong id='state_layer_message'>- / -</strong>"+busyIndicator+"<br/></span>");
//
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
        }

        var printerDisplay = null;
        // receive data from server
        self.onDataUpdaterPluginMessage = function (plugin, data) {

            if (plugin != PLUGIN_ID) {
                return;
            }
            if (data.disablePrint){
                $("#job_print").attr("disabled", "disabled");
                return
            }
            if (data.enablePrint){
                $("#job_print").removeAttr("disabled");
                return
            }

            if ("busy" in data){
                if (data.busy == true) {
                    $(".dlp-state-busyIndicator").show();
                } else {
                    $(".dlp-state-busyIndicator").hide();
                    $("#job_print").removeAttr("disabled");
                }
            } else {
                $(".dlp-state-busyIndicator").hide();
                $("#job_print").removeAttr("disabled");
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
                    document.title =   data.browserTitle.message;
                } else {
                    document.title = self.defaultBrowserTitleMessage + " " + data.browserTitle.message;
                }
            }

            // StatusBar
            // visibility of height/layer in statebar
//            if (data.showHeightInStatusBar != null){
//                if(data.showHeightInStatusBar == true){
//                    $("#heightStateOutput").show();
//                } else {
//                    $("#heightStateOutput").hide();
//                }
//            }
//            if (data.showLayerInStatusBar != null){
//                if (data.showLayerInStatusBar == true){
//                    $("#layerStateOutput").show();
//                } else {
//                    $("#layerStateOutput").hide();
//                }
//            }
//            // State Layer
//            if (data.stateMessage){
//                var layerElement = document.getElementById("state_layer_message");
//                if (layerElement != null && data.stateMessage != null) {
//                    layerElement.innerHTML = data.stateMessage;
//                }
//            }
//            // State Height
//            if (data.heightMessage){
//                var heightElement = document.getElementById("state_height_message");
//                if (heightElement != null && data.heightMessage != null) {
//                    heightElement.innerHTML = data.heightMessage;
//                }
//            }

			// Printer Display
            if ( (printerDisplay == null && data.initPrinterDisplay) ||
                  data.initPrinterDisplay){
                if (printerDisplay != null){
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
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        // Elements to bind to, e.g. #settings_plugin_DisplayLayerProgress, #tab_plugin_DisplayLayerProgress, ...
        //elements: [document.getElementById("progressinfo_plugin_navbar")]
        elements: [
            document.getElementById("displayLayerProgress_plugin_navbar"),
            document.getElementById("displayLayerProgress_plugin_settings")
        ]
    });
});
