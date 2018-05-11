# DisplayLayerProgress

A OctoPrint-Plugin that sends the current progress of a print via M117 command to the printer-display and also to the top navigation bar.

A new feature is the "Desktop Printer-Display", which shows all M117 messages in a Desktop PopUp.

It shows the **percentage, the current layer, total layer count, current height and total height**:

- Printer Display: 50% L=60/120 H=23mm/47mm  
- NavBar: Layer: 60 / 120 Height: 23mm of 47mm

*Output pattern is adjustable!*


**ATTENTION:** 
- The layer information works only when the slicer adds "layer-indicator" to the g-code (CURA-Example as comments like ```;LAYER:10```). Then these indicators are parsed via a regular-expression.
- Currently supported slicers: CURA, Simplify3D, KISSlicer. You can add your own layer-expressions in Plugin-Settings.
If you want to use "slic3r", see [Enhancement #8](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/8)
- Sometimes there is a "Post Processing script" that deletes all comments (e.g. see [Issue #33](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/issues/33))
- You need to upload your G-Code after installation of the plugin again (if you want to reuse already stored models in OctoPrint), because while uploading the G-Code is modfied
- The total height "calculation" can be done in two ways: 1)the max Z-Value in the G-Code, 2) max Z-Value with extrusion in this height
- The height/layer information is sometimes not matching with G-Code Viewer, because the viewer did a lot of "magic" (e.g. add extrusion diameter to height)

**Comment Format Examples:**

CURA: ```;LAYER:10```

Simplify3D: ```; layer 10, Z = 1.640```

The implementation is based on four steps:

1. PreProcessing the uploaded G-Code (replace layer-comment with M117) 
2. Read total layer count from G-Code before start (used last layer-comment)
3. G-Code-Hook to collect the current layer information (M117-command from step 1)
4. Progress-Hook to write all information to the printer/navbar


![navbar](screenshots/navbar.jpg "Progress in NavBar")
![statebar](screenshots/statebar.jpg "Progress in StateBar")
![desktopPrinterdisplay](screenshots/printerDisplay_popup.jpg "Desktop Printer-Display")
![printerdisplay](screenshots/example-printer-display.jpg "Progress in Printer-Display")

 
## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/archive/master.zip


## Configuration

It is possible to change the Output. See Plugin-Settings:


## Versions
see [Release-Overview](https://github.com/OllisGit/OctoPrint-DisplayLayerProgress/releases/)



