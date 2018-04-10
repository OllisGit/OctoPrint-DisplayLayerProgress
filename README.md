# DisplayLayerProgress

A OctoPrint-Plugin that sends the current progress of a print via M117 command to the printer-display and also to the top navigation bar.

It shows the percentage, the current layer and the total layer count:

- Printer Display: 50% 60/120
- NavBar: Process: 50% Layer: 60/120

ATTENTION: The layer information output only works with Cura generated G-Code, because Cura insert the layer information (layer, layerCount) as comments in the file.

![alt text](https://plugins.octoprint.org/assets/img/plugins/DisplayLayerProgress/example-navbar-display.jpg "Progress in NavBar")
![alt text](https://plugins.octoprint.org/assets/img/plugins/DisplayLayerProgress/example-printer-display.jpg "Progress in Printer-Display")

The implementation is based on four steps:

1. PreProcessing the uploaded GCode (replace layer-comment with M117) 
2. Read total layer count from G-Code before start
3. GCode-Hook to collect the current layer information (M117-command from step 1)
4. Progress-Hook to write all information to the printer/navbar
 
## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/master.zip


## Configuration

No configuration needed

