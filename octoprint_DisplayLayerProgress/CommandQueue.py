# coding=utf-8
from __future__ import absolute_import

import re
from queue import Queue
from queue import Empty
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
        self._isPrintJobRunning = False
        self._threadCount = 0

    def initCommandQueue(self, workerMethod):
        self._workerMethod = workerMethod

    def addToQueue(self, commandKey):
        self._executionCommandQueue.put(commandKey)
        self._startQueue()
        pass

    def printJobStarted(self):
        self._threadCount = 0
        self._isPrintJobRunning = True

    def printJobStopped(self):
        self._isPrintJobRunning = False


    def _startQueue(self):
        if (self._isQueueRunning == False):
            self._worker = Thread(target=self._processQueue, args=(self._workerMethod,))
            self._threadCount += 1
            self._logger.info("ThreadCount: "+str(self._threadCount) + " for worker: " + str(self._workerMethod))
            self._isQueueRunning = True
            self._worker.start()
        pass

    def _processQueue(self, workerMethod):
        # run if queue is full or the printjob is still printing
        while (self._executionCommandQueue.empty() == False or self._isPrintJobRunning == True):
            try:
                commandKey = self._executionCommandQueue.get(timeout=5*60)  # wait max 5 mintues. after that, check if job still running
                workerMethod(commandKey)
                #time.sleep(3)
                self._executionCommandQueue.task_done()
            except Empty:
                self._logger.info("queue is still empty")
                pass

        self._isQueueRunning = False
        pass

# def myQueuWorker(commandKey):
#     print("work")
#
# print("START")
# myCommandQueue = CommandQueue()
#
# myCommandQueue.initCommandQueue(myQueuWorker)
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
#
# myCommandQueue.printJobStarted()
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
# time.sleep(6)
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
# myCommandQueue.printJobStopped()
# time.sleep(6)
# myCommandQueue.addToQueue("CommandQueue.EVENTTYPE_SYSTEM")
#
# time.sleep(20)
# print("END")

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
