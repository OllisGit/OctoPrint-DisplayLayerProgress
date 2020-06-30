# Created by Wayne Porter

from ..Script import Script

class InsertAtLayerChangeEnhancement(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name": "Insert at layer change (enhancement)",
            "key": "InsertAtLayerChangeEnhancement",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "insert_location":
                {
                    "label": "When to insert",
                    "description": "Whether to insert code before or after layer change.",
                    "type": "enum",
                    "options": {"before": "Before", "after": "After"},
                    "default_value": "before"
                },
                "gcode_to_add":
                {
                    "label": "GCODE to insert.",
                    "description": "GCODE to add before or after layer change. You can add '[layer_num]' as a placeholder for the current layer number",
                    "type": "str",
                    "default_value": ""
                }
            }
        }"""

    def execute(self, data):
        gcode_to_add = self.getSettingValueByKey("gcode_to_add") + "\n"
        for layer in data:
            # Check that a layer is being printed
            lines = layer.split("\n")
            for line in lines:
                if ";LAYER:" in line:
                    index = data.index(layer)
                    layerNumber = line[7:]
                    newGcode_to_add = gcode_to_add.replace("[layer_num]", layerNumber)
                    if self.getSettingValueByKey("insert_location") == "before":
                        layer = newGcode_to_add + layer
                    else:
                        layer = layer + newGcode_to_add

                    data[index] = layer
                    break
        return data
