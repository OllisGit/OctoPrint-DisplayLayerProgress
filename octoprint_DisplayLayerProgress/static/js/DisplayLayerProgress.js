/*
 * View model for DisplayLayerProgress
 *
 * Author: Olli
 * License: AGPLv3
 */
$(function() {
    function DisplaylayerprogressViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.
        self.progressMessage = ko.observable();

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            //alert("data")
            if (plugin != "DisplayLayerProgress") {
                return;
            }
            self.progressMessage(data.progressMessage);
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: DisplaylayerprogressViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /*  */
            "loginStateViewModel", "settingsViewModel"
        ],
        // Elements to bind to, e.g. #settings_plugin_DisplayLayerProgress, #tab_plugin_DisplayLayerProgress, ...
        elements: [ /* ... */
            document.getElementById("progressinfo_plugin_navbar")
        ]
    });
});
