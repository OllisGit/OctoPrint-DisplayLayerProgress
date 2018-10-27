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
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnNavBar(data.showOnNavBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showOnPrinterDisplay(data.showOnPrinterDisplay);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showAllPrinterMessages(data.showAllPrinterMessages);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.navBarMessagePattern(data.navBarMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayMessagePattern(data.printerDisplayMessagePattern);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayScreenLocation(data.printerDisplayScreenLocation);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.printerDisplayWidth(data.printerDisplayWidth);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.addTrailingChar(data.addTrailingChar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.layerExpressions(data.layerExpressions);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showLayerInStatusBar(data.showLayerInStatusBar);
                                self.settingsViewModel.settings.plugins.DisplayLayerProgress.showHeightInStatusBar(data.showHeightInStatusBar);
        });


        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];

        self.navBarMessage = ko.observable();

        // startup
        self.onStartup = function () {
            //alert("hallo");
            var element = $("#state").find(".accordion-inner .progress");
            if (element.length) {
                var busyIndicator = " <i class='fa fa-spinner fa-spin busyIndicator' style='display:none'></i>";

                // height
                var label = gettext("Current Height");
                var tooltip = gettext("Might be inaccurate!");
                element.before("<span id='heightStateOutput' style='display:none'><span title='" + tooltip + "'>" + label + "</span>" + ": "
                    + "<strong id='state_height_message'>- / -</strong>"+busyIndicator+"  <br/></span>");
                // layer
                label = gettext("Layer");
                tooltip = gettext("Shows the layer information");
                element.before("<span id='layerStateOutput' style='display:none'> <span title='" + tooltip + "'>" + label + "</span>" + ": "
                    + "<strong id='state_layer_message'>- / -</strong>"+busyIndicator+"<br/></span>");

                // call backend for update navbar and printer-display
                OctoPrint.get("api/plugin/"+PLUGIN_ID);
            }

            $("#layerExpressionTextArea").numberedtextarea();
        };

        var printerDisplay = null;
        // receive data from server
        self.onDataUpdaterPluginMessage = function (plugin, data) {

            if (plugin != PLUGIN_ID) {
                return;
            }

            if (data.busy){
                $(".busyIndicator").show();
            } else {
                $(".busyIndicator").hide();
            }

            // NavBar
            if (data.navBarMessage){
                self.navBarMessage(data.navBarMessage);
            }

            // visibility of height/layer in statebar
            if (data.showHeightInStatusBar != null){
                if(data.showHeightInStatusBar == true){
                    $("#heightStateOutput").show();
                } else {
                    $("#heightStateOutput").hide();
                }
            }
            if (data.showLayerInStatusBar != null){
                if (data.showLayerInStatusBar == true){
                    $("#layerStateOutput").show();
                } else {
                    $("#layerStateOutput").hide();
                }
            }
            // State Layer
            if (data.stateMessage){
                var layerElement = document.getElementById("state_layer_message");
                if (layerElement != null && data.stateMessage != null) {
                    layerElement.innerHTML = data.stateMessage;
                }
            }
            // State Height
            if (data.heightMessage){
                var heightElement = document.getElementById("state_height_message");
                if (heightElement != null && data.heightMessage != null) {
                    heightElement.innerHTML = data.heightMessage;
                }
            }
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
			if (data.printerDisplay && printerDisplay != null){
                printerDisplay.update({
                    text: '<h3 class="fontsforweb_fontid_507"><font color="lightblue" style="background-color:blue;">'+data.printerDisplay+'</font></h3>'
                });
			}
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
        elements: [document.getElementById("progressinfo_plugin_navbar")]
    });
});
