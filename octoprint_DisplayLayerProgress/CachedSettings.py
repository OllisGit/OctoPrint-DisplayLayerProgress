# coding=utf-8
from __future__ import absolute_import


class CachedSettings():

    cacheEnabled = True
    cacheDict = {}

    def __init__(self, pluginSettings):
        self._pluginSettings = pluginSettings

    def updateSettings(self, pluginSettings):
        self._pluginSettings = pluginSettings
        self.cacheDict = {}


    def getStringValue(self, settingsKey):
        value = self._getValueFromCache(settingsKey)
        if (value == None):
            # try to read from real settings
            value = self._pluginSettings.get([settingsKey])
            # add to cache if needed
            if (value != None and self.cacheEnabled == True):
                self.cacheDict[settingsKey] = value

        return value

    def getIntValue(self, settingsKey):
        value = self._getValueFromCache(settingsKey)
        if (value == None):
            # try to read from real settings
            value = self._pluginSettings.get_int([settingsKey])
            # add to cache if needed
            if (value != None and self.cacheEnabled == True):
                self.cacheDict[settingsKey] = value

        return value

    def getBooleanValue(self, settingsKey):
        value = self._getValueFromCache(settingsKey)
        if (value == None):
            # try to read from real settings
            value = self._pluginSettings.get_boolean([settingsKey])
            # add to cache if needed
            if (value != None and self.cacheEnabled == True):
                self.cacheDict[settingsKey] = value

        return value

    def _getValueFromCache(self, settingsKey):
        value = None
        if (self.cacheEnabled == True):
            if (settingsKey in self.cacheDict):
                value = self.cacheDict[settingsKey]
        return value

