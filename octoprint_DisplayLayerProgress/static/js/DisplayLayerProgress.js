/*
 * View model for DisplayLayerProgress
 *
 * Author: Olli
 * License: AGPLv3
 */
$(function () {
    function DisplaylayerprogressViewModel(parameters) {
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

                var label = gettext("Layer") + ": ";
                var tooltip = gettext("Shows the layer information");

                element.before(label + "<strong title='" + tooltip + "' ><span id='state_layer_message'>- / -</span></strong></div><br>");
            }
        };

        // receive data from server
        self.onDataUpdaterPluginMessage = function (plugin, data) {

            if (plugin != "DisplayLayerProgress") {
                return;
            }

            self.navBarMessage(data.navBarMessage);

            var layerElement = document.getElementById("state_layer_message");
            if (layerElement != null && data.stateMessage != null) {
                layerElement.innerHTML = data.stateMessage;
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
