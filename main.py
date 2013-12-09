import Tkinter
import time
import threading
import random
import Queue
from subprocess import check_output
import os
import sys


class View:

    def __init__(self, master, queue, onLoadClick, onDownloadClick, onResetClick, onInstallClick, onRemoveLocalClick, onEndClick):
        self.queue = queue

        # Buttons
        btn_load = Tkinter.Button(
            master, text='Load', command=onLoadClick, width=63)
        btn_load.grid(row=0, column=0, columnspan=4)

        btn_download = Tkinter.Button(
            master, text='Download', command=onDownloadClick, width=13)
        btn_download.grid(row=1, column=0, sticky='NW')

        btn_reset = Tkinter.Button(
            master, text='Reset', command=onResetClick, width=13)
        btn_reset.grid(row=1, column=1, sticky='NW')

        btn_install = Tkinter.Button(
            master, text='Install', command=onInstallClick, width=13)
        btn_install.grid(row=1, column=2, sticky='NW')

        btn_removeLocal = Tkinter.Button(
            master, text='Remove Local APKs', command=onRemoveLocalClick, width=13)
        btn_removeLocal.grid(row=1, column=3, sticky='NW')

        btn_end = Tkinter.Button(
            master, text='Exit', command=onEndClick, width=13)
        btn_end.grid(row=20, column=3, sticky='NW')

        # On device labels
        lbl_packages_headline = Tkinter.Label(
            master, text="Apps on device")
        lbl_packages_headline.grid(row=3, column=0, columnspan=4, sticky='NW')

        self.lbl_packages = Tkinter.Label(master, justify="left")
        self.lbl_packages.grid(row=4, column=0, columnspan=4, sticky='NW')

        # local labels
        lbl_local_headline = Tkinter.Label(
            master, text="Local apps")
        lbl_local_headline.grid(row=5, column=0, columnspan=4, sticky='NW')

        self.lbl_apks = Tkinter.Label(master, justify="left")
        self.lbl_apks.grid(row=6, column=0, columnspan=4, sticky="NW")

        # status labels
        lbl_status_headline = Tkinter.Label(
            master, text="Status")
        lbl_status_headline.grid(row=7, column=0, columnspan=4, sticky='NW')

        self.lbl_status = Tkinter.Label(master, justify="left")
        self.lbl_status.grid(row=8, column=0, columnspan=4, sticky="NW")

    # Periodic Process to check message queue
    def processIncoming(self):
        while self.queue.qsize():
            try:
                msg = self.queue.get(0)
                # Check message queue and update label texts accordingly
                if msg[0] == 'packages':
                    if isinstance(msg[1], basestring):
                        self.lbl_packages.config(text=msg[1])
                    else:
                        self.lbl_packages.config(text='\n'.join(msg[1]))
                elif msg[0] == "apks":
                    if isinstance(msg[1], basestring):
                        self.lbl_apks.config(text=msg[1])
                    else:
                        self.lbl_apks.config(text='\n'.join(msg[1]))
                elif msg[0] == "status":
                    if isinstance(msg[1], basestring):
                        self.lbl_status.config(text=msg[1])
                    else:
                        self.lbl_status.config(text='\n'.join(msg[1]))

            except Queue.Empty:
                pass


class Control:

    def __init__(self, master):
        self.master = master

        # Create the queue
        self.queue = Queue.Queue()
        self.packages = 0
        self.localApks = 0
        self.remoteApks = 0

        self.gui = View(
            master, self.queue, self.onLoadClick, self.onDownloadClick,
            self.onResetClick, self.onInstallClick, self.onRemoveLocalClick, self.onEndClick)

        # Set up the thread to do asynchronous I/O
        # More can be made if necessary
        self.running = 1
        # self.thread1 = threading.Thread(target=self.workerThread1)
        # self.thread1.start()

        # Start the periodic call in the GUI to check if the queue contains
        # anything
        self.periodicCall()

    def periodicCall(self):
        self.gui.processIncoming()
        if not self.running:
            # This is the brutal stop of the system. You may want to do
            # some cleanup before actually shutting it down.
            sys.exit(1)
        self.master.after(100, self.periodicCall)

    def downloadPackages(self):
        for packagePath in self.remoteApks:
            check_output(['adb', 'pull', packagePath, 'apps'])
        self.queryLocalApks()

    def removePackages(self):
        for package in self.packages:
            self.queue.put(["status", "Uninstalling " + package])
            check_output(['adb', 'shell', 'pm', 'uninstall', package])
        self.queue.put(["status", "Done"])
        self.queryPackages()

    def installPackages(self):
        for apk in self.localApks:
            self.queue.put(["status", "Installing " + apk])
            check_output(['adb', 'install', "apps/" + apk])
        self.queue.put(["status", "Done"])
        self.queryPackages()

    def removeLocalApks(self):
        for app in os.listdir('apps'):
            os.remove('apps/' + app)
        self.queryLocalApks()

    # EVENTS

    def onLoadClick(self):
        thread = threading.Thread(target=self.queryPackages)
        thread.start()
        thread2 = threading.Thread(target=self.queryLocalApks)
        thread2.start()
        thread3 = threading.Thread(target=self.queryRemoteApks)
        thread3.start()

    def onDownloadClick(self):
        self.setLocalApks("loading...")
        thread = threading.Thread(target=self.downloadPackages)
        thread.start()

    def onResetClick(self):
        thread = threading.Thread(target=self.removePackages)
        thread.start()

    def onInstallClick(self):
        thread = threading.Thread(target=self.installPackages)
        thread.start()

    def onEndClick(self):
        self.queue.put("Bye")
        self.queue.put("Bye")
        self.running = 0

    def onRemoveLocalClick(self):
        thread = threading.Thread(target=self.removeLocalApks)
        thread.start()

    # SETTER

    def setRemoteApks(self, apks):
        print "setRemoteApks"
        print apks
        self.remoteApks = apks

    def setPackages(self, packages):
        print "setPackages"
        print packages
        self.queue.put(["packages", packages])
        self.packages = packages

    def setLocalApks(self, apks):
        print "setLocalApks"
        print apks
        self.queue.put(["apks", apks])
        self.localApks = apks

    # QUERIES

    def queryRemoteApks(self):
        # list apk files from third party only
        apks = check_output(
            ['adb', 'shell', 'pm', 'list', 'packages', '-f', '-3']).split('\r\n')
        apks.pop()
        # right split on ':' to remove 'package:'
        # left  split on '=' to remove
        for i, apk in enumerate(apks):
            apks[i] = apk.split(':')[1].split('=')[0]
        self.setRemoteApks(apks)

    def queryPackages(self):
        self.setPackages("loading...")
        packages = check_output(
            ['adb', 'shell', 'pm', 'list', 'packages', '-3']).split('\r\n')
        packages.pop()
        # right split on ':' to remove 'package:'
        for i, package in enumerate(packages):
            packages[i] = package.split(':')[1]
        self.setPackages(packages)

    def queryLocalApks(self):
        self.setLocalApks(os.listdir('apps'))

rand = random.Random()
root = Tkinter.Tk()

client = Control(root)
root.mainloop()
