import socket
import os
import sys
import _thread
import threading
import hashlib
import time
from tkinter import filedialog
import tkinter as tk


class fingerTableEntry:
    key = -1
    port = -1
    IPadd = '127.0.0.1'
    value = -1

    # key(int): key value of the node
    # port(int): port number used by node
    # IP(string): ip address of node
    # value: the key value this node is representing in the fingertable

    def __init__(self, pKey=-1, pPort=-1, pIP='127.0.0.1', pValue=-1):
        self.key = pKey
        self.port = pPort
        self.IPadd = pIP
        self.value = pValue


class node:
    # own details
    port = -1
    ip = '127.0.0.1'
    key = -1
    port_str = '-1'
    key_str = '-1'

    # predecessor details
    predKey = -1
    predPort = -1

    # successor's details (only to be used when fingertable not made)
    successorKey = -1
    successorPort = -1

    # successor's successor details
    suc_suc = -1
    suc_suc_key = -1

    # fingertable containing addresses of other node
    fingerTable = []

    # thread loops condition
    consequence = True

    # size of DHT = 2^m
    m = 6

    # increased when unable to contact successor
    count = 0

    # Lets all threads know if successor suspected to be offline
    suc_unsure = False

    # key of node that is currently leaving
    lastLeft = -1

    # key of node that just joined
    lastNewJoin = -1

    # flag indicating if fingertable available for use
    fingertableSet = False

    # contains (key, port) tuples for any new joins that
    #   informed of their arrival while fingertable was being configured
    newJoin = []

############################################# Setup Node ########################################################

    def __init__(self, own_port, other_port=None):
        # data check:
        try:
            portInt = int(own_port)
            if(portInt > 65535 or portInt < 0):
                raise ValueError
        except:
            print("port needs to be an integer between 0 - 65535")
            sys.exit()

        # If there is no reference node given, this is the first node in the chord.
        if other_port is None:

            self.port = portInt
            self.port_str = own_port
            self.key = self.hashery(own_port)
            self.key_str = str(self.key)
            self.predKey = self.key
            self.predPort = self.port

            for i in range(0, self.m):
                self.fingerTable.append(fingerTableEntry())
                self.fingerTable[i].key = self.key
                self.fingerTable[i].port = self.port
                self.fingerTable[i].IPadd = self.ip
                self.fingerTable[i].value = ((self.key+(2**i)) % (2**self.m))

            self.fingertableSet = True

            # start listening at port
            t1 = threading.Thread(target=self.listener, args=())
            t1.start()

        # NOT the first node to join
        else:
            # data check
            try:
                otherPortInt = int(other_port)
                if(otherPortInt > 65535 or otherPortInt < 0):
                    raise ValueError
            except:
                print("port needs to be an integer between 0 - 65535")
                sys.exit()

            self.port = portInt
            self.port_str = own_port
            self.key = self.hashery(own_port)
            self.key_str = str(self.key)

            self.connectToChord(otherPortInt)

            # start listening at port assigned as necessary for fingertable construction
            t1 = threading.Thread(target=self.listener, args=())
            t1.start()

            self.createFingerTable()
            self.fileGet()

        self.mainController()

    # Name:    mainController
    # Purpose: Control main functions of node concurrently using multithreading
    #          thread 1 allows the node to deal with any incoming requests (called in constructor)
    #          thread 2 is the UI that user has access to perform the functions available
    #          thread 3 responsible for maintaining the dht
    # parem:   none
    # returns: none

    def mainController(self):
        t2 = threading.Thread(target=self.options, args=())
        t3 = threading.Thread(target=self.checkSuccessor, args=())

        t2.start()
        t3.start()

    # Name:    connectToChord
    # Purpose: setup successor node using reference node and
    #          setup predecessor using the successor node
    # parem:   otherPort (string): reference node given
    # returns: none

    def connectToChord(self, otherPort):
        try:
            z = socket.socket()
            z.connect((self.ip, otherPort))

        except:
            print("the reference node is not online. Kindly find another")
            sys.exit()

        # find successor using reference node
        while True:
            toSend = 'findSuccessor ' + self.key_str
            z.send(toSend.encode())
            ans = z.recv(1024).decode()
            ansSplit = ans.split(' ')

            self.successorPort = int(float(ansSplit[0]))
            self.successorKey = int(float(ansSplit[1]))
            existsAlready = ansSplit[2]

            if(existsAlready == 'False'):
                break

            # if node with key exists then give it new one
            else:
                self.key = (self.key+1) % (2**self.m)
                self.key_str = str(self.key)

        z.send('end'.encode())

        t = socket.socket()
        t.connect((self.ip, self.successorPort))

        # find predecessor of successor as that is now our predecessor
        t.send('getPredInfo'.encode())
        ans = t.recv(1024).decode()
        nextPred = ans.split(' ')
        self.predPort = int(float(nextPred[0]))
        self.predKey = int(float(nextPred[1]))

        # inform successor that we are it's new predecessor
        toSend = 'updatePred ' + self.port_str + ' '+self.key_str
        t.send(toSend.encode())
        dump = t.recv(1024).decode()

        # Let the nodes in the DHT know of new node joining
        toSend = 'newJoin ' + self.key_str + ' ' + self.port_str
        t.send(toSend.encode())
        ans = t.recv(1024).decode()
        t.send('end'.encode())

    # Name:    createFingerTable
    # Purpose: creates fingertable for the node using the successor
    #          fingertable contains entries for addresses of nodes
    #          responsible for key value x + 2^k
    #          where x is node's own key value and
    #          k is from 0 - m
    # parem:   none
    # returns: none

    def createFingerTable(self):
        totalEntries = self.m
        predictedEntries = []
        DHTsize = 2**self.m

        for i in range(0, totalEntries):
            predictedEntries.append((self.key+(2**i)) % DHTsize)

        tmpfingerTable = fingerTableEntry(
            self.successorKey, self.successorPort, self.ip, int(predictedEntries[0]))
        self.fingerTable.append(tmpfingerTable)

        for i in range(1, totalEntries):
            # successor will help fill our fingertable
            s = socket.socket()
            s.connect((self.ip, self.successorPort))
            toSend = 'findSuccessor ' + str(predictedEntries[i])
            s.send(toSend.encode())
            temp = s.recv(1024).decode()

            # convert temp to port and key then store in finger table
            tempSplit = temp.split(' ')
            tmpfingerTable = fingerTableEntry()
            tmpfingerTable.key = int(tempSplit[1])
            tmpfingerTable.port = int(tempSplit[0])
            tmpfingerTable.IPadd = self.ip
            tmpfingerTable.value = int(predictedEntries[i])

            self.fingerTable.append(tmpfingerTable)

        s.send('end'.encode())

        self.fingertableSet = True
        self.stablizeFingertable()

    def stablizeFingertable(self):
        for newEntry in self.newJoin:
            for node in self.fingerTable:
                if (newEntry[0] >= node.value and newEntry[0] < node.key):
                    node.key = newEntry[0]
                    node.port = newEntry[1]

                elif (node.key < node.value and newEntry[0] < node.key):
                    node.key = newEntry[0]
                    node.port = newEntry[1]

                elif (node.key < node.value and newEntry[0] >= node.value):
                    node.key = newEntry[0]
                    node.port = newEntry[1]

        self.newJoin = []

    # Name:    fileGet
    # Purpose: Node gets files that fall under it's key space
    #          from successor after joining
    # parem:   none
    # returns: none

    def fileGet(self):
        s = socket.socket()
        s.connect((self.ip, self.fingerTable[0].port))
        toSend = 'fileGet '+self.key_str
        s.send(toSend.encode())
        numOfFiles = int(s.recv(1024).decode())
        s.send('ack'.encode())

        while(numOfFiles):
            ans = s.recv(1024).decode()
            fileList = ans.split(' ')
            filename = fileList[0]
            size = int(fileList[1])
            file = os.path.join(self.key_str, filename)
            s.send('ack'.encode())

            if(not os.path.exists(self.key_str)):
                os.makedirs(self.key_str)

            total_recieved = 0
            with open(file, 'wb+') as f:
                while total_recieved < size:
                    string = s.recv(1024)
                    total_recieved += len(string)
                    f.write(string)

            s.send('ack'.encode())

            numOfFiles -= 1


############################################# User Handler (thread 2 - t2) #######################################################

    # Name:    options
    # Purpose: Allow user to use functions provided by the node
    # parem:   none
    # returns: none

    def options(self):
        print("Welcome to the DHT. Kindly pick one of the options to proceed")
        while(self.consequence):  # change this to global etc etc explained above
            print("")
            print("choose an option:")
            print("1. Store a File")
            print("2. Find a File")
            print("3. Files stored here")
            print("4. FingerTable details")
            print("5. logout")
            print("")

            choice = input("=> ")
            if choice == '1':
                self.PUT()

            elif choice == '2':
                self.GET()

            elif choice == '3':
                self.viewFiles()

            elif choice == '4':
                self.printFingerTable()

            elif choice == '5':
                self.handleLogout()

            else:
                print("invalid choice\n")

    # Name:    PUT
    # Purpose: Store files into the system by creating it's key.
    #          Find the correct node to store the file and then send it to it.
    # parem:   none
    # returns: none

    def PUT(self):
        filepath = self.fileDialog('getFile')

        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)

            filename = filepath.split('/')[-1]
            print('filename: ', filename)

            file_key = self.hashery(filename)
            print('filename key: ', file_key)
            node = self.findSuccessor(file_key)

            user = node.split(' ')

            z = socket.socket()
            z.connect((self.ip, int(user[0])))
            toSend = 'store ' + filename + ' ' + str(size)
            z.send(toSend.encode())
            ack = z.recv(1024).decode()

            f = open(filepath, 'rb')
            for chunk in iter(lambda: f.read(1024), b''):
                z.send(chunk)

            ack = z.recv(1024).decode()
            f.close()
            z.send('end'.encode())

        else:
            print("either file doesnot exist or no file selected")

    # Name:    GET
    # Purpose: Find the required file from the system using it's key.
    #          Contact the node with the file and get the file if exists
    # parem:   none
    # returns: none

    def GET(self):
        filename = input('name of file: ')
        hash_of_file = self.hashery(filename)

        node_with_file = self.findSuccessor(hash_of_file)
        user = node_with_file.split(' ')

        z = socket.socket()
        z.connect((self.ip, int(user[0])))
        toSend = 'get ' + filename
        z.send(toSend.encode())
        reply = z.recv(1024).decode()

        if(reply == 'file not found'):
            print('\n file doesnot exist \n')
        else:
            data = reply.split(' ')
            filename = ' '.join(data[0:-1])
            size = int(data[-1])

            z.send('ack'.encode())

            dir = self.fileDialog('getDir')
            file = os.path.join(dir, filename)

            f = open(file, "wb+")
            total_recieved = 0
            while total_recieved < size:
                string = z.recv(1024)
                total_recieved += len(string)
                f.write(string)

            print('file downloaded')

        z.send('end'.encode())

    # Name:    viewFiles
    # Purpose: Lets user view names of files stored at own node
    # parem:   none
    # returns: none

    def viewFiles(self):
        if(os.path.exists(self.key_str)):
            fileList = os.listdir(self.key_str)
            if(len(fileList) > 0):
                print('\n files present: ')
                print(fileList)
                print("")

            else:
                print("\n No files present \n")

        else:
            print('\n no files present \n')

    # Name:    printFingerTable
    # Purpose: Lets user view the address of node responsible for position x + 2^(k)
    #          where x is the node's own position value
    #                k any integer from 0 - log2(total space of DHT)
    # parem:   none
    # returns: none

    def printFingerTable(self):
        print("-----------------------")
        print("My Key : " + self.key_str)
        print("Pred Info " + str(self.predKey) + ' ' + str(self.predPort))
        print("suc of suc " + str(self.suc_suc_key) + ' '+str(self.suc_suc))
        print()
        print('Key | Port Num | value')
        print("-----------------------")
        for entry in self.fingerTable:
            if(entry.key % 10 == entry.key and entry.port % 10000 == entry.port):
                print('  ' + str(entry.key) + ' |   ' +
                      str(entry.port) + '   | ' + str(entry.value))
            elif(entry.key % 10 == entry.key):
                print('  ' + str(entry.key) + ' |   ' +
                      str(entry.port) + '  | ' + str(entry.value))
            elif(entry.port % 10000 == entry.port):
                print(' ' + str(entry.key) + ' |   ' +
                      str(entry.port) + '   | ' + str(entry.value))
            else:
                print(' ' + str(entry.key) + ' |   ' +
                      str(entry.port) + '  | ' + str(entry.value))
        print("-----------------------")

    # Name:    handleLogout
    # Purpose: called when user chooses to shut node down.
    #          informs other nodes its about to leave and sends
    #          its files to their successor
    # parem:   none
    # returns: none

    def handleLogout(self):
        # if only node in the DHT
        if(self.fingerTable[0].port == self.port):
            self.consequence = False
            print("logging out")
            _thread.exit()

        self.logoutFileHandler()
        self.informPred()
        self.nodeLeft(
            self.port, self.fingerTable[0].port, self.fingerTable[0].key)

        # shuts down infinite loops in all three threads
        self.consequence = False

        # send one last request to self in case it is blocking
        try:
            z = socket.socket()
            z.connect((self.ip, self.port))
            z.send('end'.encode())
            print('logging out')
        except:
            print('logging out')

    # Name:    logoutFileHandler
    # Purpose: sends current node's files to their will be
    #          successor after this node goes offline
    # parem:   none
    # returns: none

    def logoutFileHandler(self):
        if(os.path.exists(self.key_str)):
            if(self.suc_unsure == True):
                time.sleep(6)

            # in every case, the node's successor will be the inheritor of the files
            try:
                z = socket.socket()
                z.connect((self.ip, int(self.fingerTable[0].port)))
            except:
                print('cannot contact successor')
                return

            file_list = os.listdir(self.key_str)

            for file in file_list:
                filename = os.path.join(self.key_str, file)
                toSend = 'store ' + \
                    file + ' ' + \
                    str(os.path.getsize(filename))
                z.send(toSend.encode())
                ack = z.recv(1024).decode()

                f = open(filename, 'rb')
                for chunk in iter(lambda: f.read(1024), b''):
                    z.send(chunk)

                ack = z.recv(1024).decode()
                f.close()
                os.remove(filename)

            os.rmdir(self.key_str)
            z.send('end'.encode())

    # Name:    informPred
    # Purpose: informs Predecessor about it's new successor
    #          for a smooth transition after the node goes offline
    # parem:   none
    # returns: none

    def informPred(self):
        try:
            z = socket.socket()
            z.connect((self.ip, int(self.predPort)))
        except:
            print('cannot contact pred')
            return

        toSend = 'your new successor ' + \
            str(self.fingerTable[0].port)
        z.send(toSend.encode())
        ack = z.recv(1024).decode()

        z.send('end'.encode())


############################################## Maintaining DHT (thread 3 - t3) ###################################################

    # Name:    checkSuccessor
    # Purpose: pings it's successor every 2 seconds to see if it is alive.
    #          if successor cannot be connected 3 times in a row, it
    #          considers it dead and considers it's successor's successor
    #          it's new successor. informs the rest of the dht about it's leaving.
    # parem:   none
    # returns: none


    def checkSuccessor(self):
        while(self.consequence):
            time.sleep(2)
            try:
                z = socket.socket()
                z.connect((self.ip, int(self.fingerTable[0].port)))

                z.send('hello'.encode())
                ans = z.recv(1024).decode()
                anssplit = ans.split(' ')

                self.suc_suc = int(float(anssplit[0]))
                self.suc_suc_key = int(float(anssplit[1]))
                z.send('end'.encode())

            except:
                if(self.count < 1):
                    self.count += 1
                    self.suc_unsure = True

                else:
                    # successor needs to be updated as he is lost
                    print("successor lost. new suc: ", self.suc_suc)

                    self.count = 0
                    self.suc_unsure = False

                    z = socket.socket()
                    z.connect((self.ip, int(self.suc_suc)))
                    toSend = 'updatePred ' + \
                        self.port_str + ' ' + self.key_str
                    z.send(toSend.encode())
                    ack = z.recv(1024).decode()
                    z.send('end'.encode())

                    self.nodeLeft(
                        self.fingerTable[0].key, self.suc_suc, self.suc_suc_key)


######################################### Request Handler (thread 1 - t1)##########################################

    # Name:    listener
    # Purpose: socket bound to address and port given at run time
    #          listening for any connections.
    # parem:   none
    # returns: none

    def listener(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.ip, self.port))
        s.listen(10)

        while(self.consequence):
            peer, addr = s.accept()
            _thread.start_new_thread(self.dealer, (peer,))

    # Name:    dealer
    # Purpose: communicates with connecting node to perform
    #          functions needed by the connecting node
    # parem:   peer(socket object): socket object of the connecting node
    # returns: none

    def dealer(self, peer):
        string = ''
        while(True):
            try:
                string = peer.recv(1024).decode()
            except:
                string = 'end'

            string_in_list = string.split(' ')

            # edge case. no peer should be sending an empty string
            if(string == ''):
                _thread.exit()

            # Predecessor checking to see if alive
            if(string == 'hello'):
                self.handlePing(peer)

            # new node has joined the DHT
            elif (string_in_list[0] == 'newJoin'):
                self.newJoinHandler(string_in_list[1], string_in_list[2])
                peer.send('done'.encode())

            # file needs to be stored on this node
            elif(string_in_list[0] == 'store'):
                self.store(peer, string)

            # file needs to be sent from this node
            elif(string_in_list[0] == 'get'):
                self.upload(peer, string_in_list[1])

            # new predecessor asking for files that belong to it
            elif(string_in_list[0] == 'fileGet'):
                self.fileSend(peer, string_in_list)

            # find node responsible for a certain key
            elif (string_in_list[0] == 'findSuccessor'):
                ans = self.findSuccessor(int(string_in_list[1]))
                peer.send(ans.encode())

            # asking for Predecessor info
            elif(string == 'getPredInfo'):
                ans = str(self.predPort) + ' ' + str(self.predKey)
                peer.send(ans.encode())

            # node informed of it's new successor
            elif(string_in_list[0] == 'your'):
                self.contactSuc(int(string_in_list[3]))
                peer.send('ack'.encode())

            # node informed of it's new predecessor
            elif(string_in_list[0] == 'updatePred'):
                self.predPort = int(string_in_list[1])
                self.predKey = int(string_in_list[2])
                peer.send('ack'.encode())

            # a node has left the system
            elif(string_in_list[0] == 'nodeLeft'):
                ans = self.nodeLeft(int(string_in_list[1]), int(
                    string_in_list[2]), int(string_in_list[3]))
                peer.send(ans.encode())

            elif(string_in_list[0] == 'completedJoin'):
                self.removeNewJoin(int(string_in_list[1]))
                peer.send('ack'.encode())

            # peer wants to end the connection
            elif(string == 'end'):
                peer.close()
                _thread.exit()

    # Name:    handlePing
    # Purpose: responds to node (predecessor) when it checks if alive
    # parem:   peer(socket object): socket object of the node
    # returns: none

    def handlePing(self, peer):
        toSend = ''
        if(self.fingertableSet):
            toSend = str(self.fingerTable[0].port) + \
                ' ' + str(self.fingerTable[0].key)
        else:
            toSend = str(self.successorPort) + ' ' + str(self.successorKey)

        peer.send(toSend.encode())

    # Name:    store
    # Purpose: stores a file which another node sends
    # parem:   peer(socket object): socket object of the connecting node
    #          msg(string): message from peer containing filename and size
    # returns: none

    def store(self, peer, msg):
        linesplit = msg.split(' ')
        filename = ' '.join(linesplit[1:-1])
        size = int(linesplit[-1])

        peer.send('ack'.encode())

        file = os.path.join(self.key_str, filename)

        if(not os.path.exists(self.key_str)):
            os.makedirs(self.key_str)

        f = open(file, 'wb+')
        totalRecieved = 0
        while totalRecieved < size:
            string = peer.recv(1024)
            totalRecieved += len(string)
            f.write(string)

        peer.send('ack'.encode())
        f.close()

    # Name:    fileSend
    # Purpose: sends connecting node (predecessor) the files that
    #          fall under it's key value
    # parem:   peer(socket object): socket object of the connecting node
    #          data(string): data sent by the connecting node
    # returns: none

    def fileSend(self, peer, data):
        if(os.path.exists(self.key_str)):
            k = int(data[1])

            listOfFiles = os.listdir(self.key_str)
            toSend = []

            s = socket.socket()
            s.connect((self.ip, self.predPort))
            s.send('getPredInfo'.encode())
            ans = s.recv(1024).decode()
            predOfPred = ans.split(' ')
            predOfPredKey = int(predOfPred[1])

            # edge case predecessor is largest node in dht
            if(k > self.key and predOfPredKey < k):
                toSend = list(
                    filter((lambda x: self.hashery(x) <= k
                            and self.hashery(x) > predOfPredKey), listOfFiles)
                )

            # edge case predecessor is smallest node in dht
            elif(k < self.key and predOfPredKey > k):
                toSend = list(
                    filter((lambda x: self.hashery(x) <= k and self.hashery(
                        x) > predOfPredKey), listOfFiles)
                )

            # general case
            elif(k < self.key):
                toSend = list(
                    filter((lambda x: self.hashery(x) <= k), listOfFiles))

            peer.send(str(len(toSend)).encode())
            ack = peer.recv(1024).decode()

            for filename in toSend:
                file = os.path.join(self.key_str, filename)
                toSend = filename + ' ' + str(os.path.getsize(file))
                peer.send(toSend.encode())
                ack = peer.recv(1024).decode()

                f = open(file, 'rb')
                for chunk in iter(lambda: f.read(1024), b''):
                    peer.send(chunk)

                ack = peer.recv(1024).decode()
                f.close()
                os.remove(file)

        else:
            peer.send('0'.encode())

    # Name:    upload
    # Purpose: sends requested file to connecting node
    # parem:   peer(socket object): socket object of the connecting node
    #          filename(string): name of file to send to connecting node
    # returns: none

    def upload(self, peer, filename):
        file = os.path.join(self.key_str, filename)
        if(os.path.exists(file)):
            size = os.path.getsize(file)

            toSend = filename + ' ' + str(size)
            peer.send(toSend.encode())
            ack = peer.recv(1024).decode()

            f = open(file, 'rb')
            for chunk in iter(lambda: f.read(1024), b''):
                peer.send(chunk)

        else:
            peer.send('file not found'.encode())

    # Name:    newJoinHandler
    # Purpose: updates it's fingertables with the new node if needed
    # parem:   pKey(string): key value of new node
    #          pPort(string): port num of new node
    # returns: none

    def newJoinHandler(self, pKey, pPort):  # Handle changes!!!!!!!!!!!!!!!!!
        iKey = int(pKey)
        iPort = int(pPort)

        if (iKey == self.key or iKey == self.lastNewJoin):
            return
        else:
            self.lastNewJoin = iKey
            if(self.fingertableSet == False):
                if((iKey, iPort) not in self.newJoin):
                    self.newJoin.append((iKey, iPort))

                s = socket.socket()
                s.connect((self.ip, self.successorPort))
                toSend = 'newJoin ' + pKey + ' ' + pPort
                s.send(toSend.encode())
                ack = s.recv(1024).decode()
                s.send('end'.encode())
                return

            # update fingertable
            for entry in self.fingerTable:

                if (iKey >= entry.value and iKey < entry.key):
                    entry.key = iKey
                    entry.port = iPort

                elif (entry.key < entry.value and iKey < entry.key):
                    entry.key = iKey
                    entry.port = iPort

                elif (entry.key < entry.value and iKey >= entry.value):
                    entry.key = iKey
                    entry.port = iPort

            prevKey = -1
            for entry in self.fingerTable:
                if (entry.key != iKey and entry.key != self.key and entry.key != prevKey):
                    prevKey = entry.key
                    s = socket.socket()
                    s.connect((self.ip, entry.port))
                    toSend = 'newJoin ' + pKey + ' ' + pPort
                    s.send(toSend.encode())
                    ack = s.recv(1024).decode()
                    s.send('end'.encode())

    # Name:    contactSuc
    # Purpose: contacts successor to inform that you are his predecessor.
    # parem:   suc_port(int): port number of successor
    # returns: none

    def contactSuc(self, suc_port):
        try:
            s = socket.socket()
            s.connect((self.ip, suc_port))
        except:
            print('cannot contact given successor')
            return

        toSend = 'updatePred ' + self.port_str + ' ' + self.key_str
        s.send(toSend.encode())
        ack = s.recv(1024).decode()
        s.send('end'.encode())

############################################### Micellaneous ##################3##################################

    # Name:    hashery
    # Purpose: finds hash key (within 0 - m) of given value
    #          where m is the size of the dht
    # parem:   to_hash (string): value to find hash of
    # returns: (int): hashed value

    def hashery(self, to_hash):
        hashie = hashlib.sha1(to_hash.encode())

        hex = hashie.hexdigest()

        num = 0
        multiplier = 2**40

        for each in hex:
            if (each >= '0' and each <= '9'):
                num += multiplier * int(each)
                multiplier /= 2
            else:
                if(each == 'a'):
                    num += multiplier * 10
                    multiplier /= 2

                elif(each == 'b'):
                    num += multiplier * 11
                    multiplier /= 2

                elif(each == 'c'):
                    num += multiplier * 12
                    multiplier /= 2
                elif(each == 'd'):
                    num += multiplier * 13
                    multiplier /= 2
                elif(each == 'e'):
                    num += multiplier * 14
                    multiplier /= 2
                elif(each == 'f'):
                    num += multiplier * 15
                    multiplier /= 2

        finalHash = int(num % (2**self.m))
        return finalHash

    # Name:    findSuccessor
    # Purpose: finds successor node of given key value
    # parem:   key (int): key value to find successor of
    # returns: (string): three components:
    #                    port of successor node
    #                    key of successor node
    #                    boolean indicating exact match

    def findSuccessor(self, key):
        # fingertable not operational
        if(self.fingertableSet == False):
            # self = key
            if(self.key == key):
                return self.port_str + ' ' + self.key_str + ' True'

            # edge case suc < self < key e.g 8 < 18 < 56
            if(self.key < key and self.successorKey < key and self.key > self.successorKey):
                return str(self.successorPort) + ' ' + str(self.successorKey) + ' False'

             # edge case key < suc < self e.g 8 < 18 < 56
            if(self.key > key and self.successorKey > key and self.key > self.successorKey):
                return str(self.successorPort) + ' ' + str(self.successorKey) + ' False'

            # self < key < suc
            if(self.key < key and key < self.successorKey and self.key < self.successorKey):
                return str(self.successorPort) + ' ' + str(self.successorKey) + ' False'

            # self < key = suc
            if(self.key < key and key == self.successorKey and self.key < self.successorKey):
                return str(self.successorPort) + ' ' + str(self.successorKey) + ' True'

            # send to successor to handle
            s = socket.socket()
            s.connect((self.ip, self.successorPort))
            toSend = 'findSuccessor ' + str(key)
            s.send(toSend.encode())
            ans = s.recv(1024).decode()
            s.send('end'.encode())
            return ans

        # else if fingertable is set
        successor = self.fingerTable[0]

        # self = key
        if(self.key == key):
            return self.port_str + ' ' + self.key_str + ' True'

        # edge case suc < self < key e.g 8 < 18 < 56
        if(self.key < key and successor.key < key and self.key > successor.key):
            return str(successor.port) + ' ' + str(successor.key) + ' False'

        # edge case key < suc < self e.g 8 < 18 < 56
        if(self.key > key and successor.key > key and self.key > successor.key):
            return str(successor.port) + ' ' + str(successor.key) + ' False'

        # self < key < suc
        if(self.key < key and key < successor.key and self.key < successor.key):
            return str(successor.port) + ' ' + str(successor.key) + ' False'

        # self < key = suc
        if(self.key < key and key == successor.key and self.key < successor.key):
            return str(successor.port) + ' ' + str(successor.key) + ' True'

        # send key to largest node < key to find it's successor
        solverKey = -1
        solverPort = -1
        largestKey = -1
        largestPort = -1
        for x in range(0, self.m):
            if(self.key != self.fingerTable[x].key and
                    self.fingerTable[x].key < key and
                    solverKey < self.fingerTable[x].key):
                solverKey = self.fingerTable[x].key
                solverPort = self.fingerTable[x].port

            if(self.key != self.fingerTable[x].key and largestKey < self.fingerTable[x].key):
                largestKey = self.fingerTable[x].key
                largestPort = self.fingerTable[x].port

        try:
            s = socket.socket()
            s.connect((self.ip, solverPort))
            toSend = 'findSuccessor ' + str(key)
            s.send(toSend.encode())
            ans = s.recv(1024).decode()
            s.send('end'.encode())
            return ans
        except:
            pass

        # could not find any node < key so send to largest key we know to figure out
        if(successor.key > self.key):
            try:
                s = socket.socket()
                s.connect((self.ip, largestPort))
                toSend = 'findSuccessor ' + str(key)
                s.send(toSend.encode())
                ans = s.recv(1024).decode()
                s.send('end'.encode())
                return ans
            except:
                pass

        # exception when nothing else
        return self.port_str + ' ' + self.key_str + ' False'

    # Name:    nodeLeft
    # Purpose: informs all entries in fingertable of the loss of a node.
    #          also gives information of it's replacement.
    #          updates it's own fingertable as well
    # parem:   key (int): key value of offline node
    #          sucPort(int): port used by replacement node
    #          sucHashKey(int):  key value of replacement node
    # returns: (string): status

    def nodeLeft(self, key, sucPort, sucHashKey):
        if key == self.lastLeft:
            return 'done'

        else:
            self.lastLeft = key

            if(self.fingertableSet == False):
                if key == self.successorKey:
                    self.successorKey = sucHashKey
                    self.successorPort = sucPort

                s = socket.socket()
                s.connect((self.ip, self.successorPort))
                toSend = 'nodeLeft ' + \
                    str(key) + ' ' + str(sucPort) + ' ' + str(sucHashKey)
                s.send(toSend.encode())
                resp = s.recv(1024).decode()
                s.send('end'.encode())

                return 'updated'

            lastKey = -1
            for entry in self.fingerTable:
                if entry.key != key and entry.key != self.key and entry.key != lastKey:
                    lastKey = entry.key
                    try:
                        s = socket.socket()
                        s.connect((self.ip, entry.port))
                    except:
                        continue
                    toSend = 'nodeLeft ' + \
                        str(key) + ' ' + str(sucPort) + ' ' + str(sucHashKey)
                    s.send(toSend.encode())
                    resp = s.recv(1024).decode()
                    s.send('end'.encode())

            # edge case lost key is the only one in fingertable
            if(lastKey == -1):
                s = socket.socket()
                s.connect((self.ip, sucPort))
                toSend = 'nodeLeft ' + \
                    str(key) + ' ' + str(sucPort) + ' ' + str(sucHashKey)
                s.send(toSend.encode())
                resp = s.recv(1024).decode()
                s.send('end'.encode())

            # update your own fingerTable
            for entry in self.fingerTable:
                if entry.key == key:
                    entry.port = sucPort
                    entry.key = sucHashKey
            return 'updated'

    # Name:    fileDialog
    # Purpose: Opens file Dialogs for GUI for getting paths
    # parem:   mode (string): requirement of user
    # returns: (string): path of file / dir

    def fileDialog(self, mode):
        root = tk.Tk()
        root.wm_attributes('-topmost', True)
        root.withdraw()
        path = ''

        if(mode == 'getFile'):
            print('\nchoose file to upload\n')
            path = filedialog.askopenfilename(parent=root)

        elif(mode == 'getDir'):
            print('\nchoose folder to download file to \n')
            path = filedialog.askdirectory()

        root.destroy()
        return path


def Main():
    if(len(sys.argv) == 3):  # additional node
        c = node(sys.argv[1], sys.argv[2])

    elif(len(sys.argv) == 2):  # first node
        c = node(sys.argv[1])

    else:
        print('for first node: python <filename> <portNum>')
        print('for any other node: python <filename> <portNum> <ReferencePortNum>')


if __name__ == '__main__':
    Main()
