# coding=utf-8
from __future__ import absolute_import

import re
from queue import Queue
from threading import Thread

import time
import logging

class CommandQueue():

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._worker = None
        self._workerMethod = None
        self._executionCommandQueue = Queue()
        self._isQueueRunning = False

    def initCommandQueue(self, workerMethod):
        self._workerMethod = workerMethod

    def addToQueue(self, commandKey):
        self._executionCommandQueue.put(commandKey)
        self._startQueue()
        pass

    def _startQueue(self):
        if (self._isQueueRunning == False):
            self._worker = Thread(target=self._processQueue, args=(self._workerMethod,))
            self._isQueueRunning = True
            self._worker.start()
        pass

    def _processQueue(self, workerMethod):
        while (self._executionCommandQueue.empty() == False):
            commandKey = self._executionCommandQueue.get()
            workerMethod(commandKey)
            #time.sleep(3)
            self._executionCommandQueue.task_done()
        self._isQueueRunning = False
        pass


## TEST ZONE
#print("START")
#myCommandQueue = CommandQueue()

#myCommandQueue.initCommandDefinitions()
#myOsCommand = OSCommand()
#myCommandQueue.addToQueue(CommandQueue.EVENTTYPE_SYSTEM, "hallowelt")
#time.sleep(3)
#myCommandQueue.addToQueue(myOsCommand)
#time.sleep(10)
#myCommandQueue.addToQueue(myOsCommand)
#time.sleep(1)
#myCommandQueue.addToQueue(myOsCommand)
#print("END")
