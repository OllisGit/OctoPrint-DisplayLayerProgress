# DisplayLayerProgress

A OctoPrint-Plugin that sends the current progress of a print via M117 command to the printer-display and also to the top navigation bar.

It shows the percentage, the current layer and the total layer count:

- Printer Display: 50% 60 / 120
- NavBar: Layer: 60 / 120

**ATTENTION:** 
- The layer information output only works with "Cura"/"Simplify3D" generated G-Code, because these Slicer insert the layer information directly as comments in the file. 
If you want to use "slic3r", see [Enhancement #8](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/8)
- If the layer comments couldn't found, only the percentage will be displayed
- You need to upload your G-Code after installation of the plugin again (if you want to reuse already stored models in OctoPrint), because while uploading the G-Code is modfied

**Comment Format Examples:**

CURA: ```;LAYER:10```

Simplify3D: ```; layer 10, Z = 1.640```

The implementation is based on four steps:

1. PreProcessing the uploaded G-Code (replace layer-comment with M117) 
2. Read total layer count from G-Code before start (used last layer-comment)
3. G-Code-Hook to collect the current layer information (M117-command from step 1)
4. Progress-Hook to write all information to the printer/navbar

![alt text](https://plugins.octoprint.org/assets/img/plugins/DisplayLayerProgress/example-navbar-display.jpg "Progress in NavBar")
![alt text](https://plugins.octoprint.org/assets/img/plugins/DisplayLayerProgress/example-printer-display.jpg "Progress in Printer-Display")

 
## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/master.zip


## Configuration

It is possible to change the Output. See Plugin-Settings:


## Versions
see [Release-Overview](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/)



