import socket
import os
import sys
import _thread
import threading
import hashlib
import time
import math


class fingerTableEntry:
    key = -1
    portNo = -1
    IPadd = '127.0.0.1'
    value = -1

    # key(int): key value of the node
    # portNo(int): port number used by node
    # IP(string): ip address of node
    # value: the key value this node is representing in the fingertable

    def __init__(self, pKey=-1, pPort=-1, pIP='127.0.0.1', pValue=-1):
        self.key = pKey
        self.portNo = pPort
        self.IPadd = pIP
        self.value = pValue


class chord:
    # own details
    port = -1
    ip = '127.0.0.1'
    key = -1

    # predecessor details
    predKey = -1
    predPort = -1

    # successor's successor details
    suc_suc = -1
    suc_suc_key = -1

    # fingertable containing addresses of other node
    fingerTable = []

    # thread loops condition
    consequence = True

    # size of DHT
    m = 64

    # increased when unable to contact successor
    count = 0

    # Lets all threads know if successor cannot be contacted
    suc_unsure = False

    # Flags
    lastLeft = -1
    lastNewJoin = -1

############################################# Setup Node ########################################################

    def __init__(self, own_port, other_port=None):

        # If there is no reference node given, this is the first node in the chord.
        if other_port is None:

            self.port = own_port
            self.key = self.hashery(own_port)
            self.predKey = self.key
            self.predPort = self.port

            for i in range(0, 6):
                self.fingerTable.append(fingerTableEntry())
                self.fingerTable[i].key = self.key
                self.fingerTable[i].portNo = int(self.port)
                self.fingerTable[i].IPadd = self.ip
                self.fingerTable[i].value = ((self.key+(2**i)) % self.m)

        # NOT the first node to join
        else:
            self.port = own_port
            self.key = self.hashery(own_port)

            successorPort, successorKey = self.connectToChord(other_port)
            self.createFingerTable(successorPort, successorKey)
            self.fileGet()

        self.mainController()

    # Name:    mainController
    # Purpose: Control main functions of node concurrently using multithreading
    #          thread 1 is the UI that user has access to perform the functions available
    #          thread 2 allows the node to deal with any incoming requests
    #          thread 3 responsible for maintaining the dht
    # parem:   none
    # returns: none

    def mainController(self):
        t1 = threading.Thread(target=self.options, args=())
        t2 = threading.Thread(target=self.listener, args=())
        t3 = threading.Thread(target=self.checkSuccessor, args=())

        t1.start()
        t2.start()
        t3.start()

    # Name:    connectToChord
    # Purpose: setup successor node using reference node and
    #          setup predecessor using the successor node
    # parem:   otherPort (string): reference node given
    # returns: successorPort (int): port number of successor node
    #          successorKey  (int): key value of successor node

    def connectToChord(self, otherPort):
        try:
            z = socket.socket()
            z.connect((self.ip, int(otherPort)))

        except:
            print("the reference node is not online. Kindly find another")
            sys.exit()

        # find successor using reference node
        toSend = 'findSuccessor ' + str(self.key)
        z.send(toSend.encode())

        ans = z.recv(1024).decode()
        ansSplit = ans.split(' ')
        successorPort = int(float(ansSplit[0]))
        successorKey = int(float(ansSplit[1]))
        z.send('end'.encode())

        t = socket.socket()
        t.connect((self.ip, successorPort))

        # find predecessor of successor as that is now our predecessor
        t.send('getPredInfo'.encode())
        ans = t.recv(1024).decode()
        nextPred = ans.split(' ')
        self.predKey = int(float(nextPred[1]))
        self.predPort = int(float(nextPred[0]))

        # inform successor that we are it's new predecessor
        toSend = 'updatePred ' + str(self.port) + ' '+str(self.key)
        t.send(toSend.encode())
        dump = t.recv(1024).decode()

        # Let the nodes in the DHT know of new node joining
        toSend = 'newJoin ' + str(self.key) + ' ' + str(self.port)
        t.send(toSend.encode())
        ans = t.recv(1024).decode()
        t.send('end'.encode())

        return successorPort, successorKey

    # Name:    createFingerTable
    # Purpose: creates fingertable for the node using the successor
    #          fingertable contains entries for addresses of nodes
    #          responsible for key value x + 2^k
    #          where x is node's own key value and
    #          k is from 0 - log2(key space in dht)
    # parem:   successorPort (int): port number of successor node
    #          successorKey  (int): key value of successor node
    # returns: none

    def createFingerTable(self, successorPort, successorKey):
        totalEntries = int(math.log2(self.m))
        predictedEntries = []

        for i in range(0, totalEntries):
            predictedEntries.append((self.key+(2**i)) % self.m)

        tmpfingerTable = fingerTableEntry(
            successorKey, successorPort, self.ip, int(predictedEntries[0]))
        self.fingerTable.append(tmpfingerTable)

        for i in range(1, totalEntries):
            # successor will help fill our fingertable
            s = socket.socket()
            s.connect((self.ip, successorPort))
            toSend = 'findSuccessor ' + str(predictedEntries[i])
            s.send(toSend.encode())
            temp = s.recv(1024).decode()

            # convert temp to port and key then store in finger table
            tempSplit = temp.split(' ')
            tmpfingerTable = fingerTableEntry()
            tmpfingerTable.key = int(tempSplit[1])
            tmpfingerTable.portNo = int(tempSplit[0])
            tmpfingerTable.IPadd = self.ip
            tmpfingerTable.value = int(predictedEntries[i])

            self.fingerTable.append(tmpfingerTable)

        s.send('end'.encode())

    # Name:    fileGet
    # Purpose: Node gets files that fall under it's key space
    #          from successor after joining
    # parem:   none
    # returns: none

    def fileGet(self):
        s = socket.socket()
        s.connect((self.ip, self.fingerTable[0].portNo))
        toSend = 'fileGet '+str(self.key)
        s.send(toSend.encode())
        numOfFiles = int(s.recv(1024).decode())
        s.send('ack'.encode())

        while(numOfFiles):
            ans = s.recv(1024).decode()
            fileList = ans.split(' ')
            filename = fileList[0]
            size = int(fileList[1])
            file = os.path.join(str(self.port), filename)
            s.send('ack'.encode())
            string = s.recv(1024).decode()

            if(not os.path.exists(self.port)):
                os.makedirs(self.port)

            with open(file, 'w+') as f:
                total_recieved = len(string)
                f.write(string)
                while total_recieved < size:
                    string = s.recv(1024).decode()
                    total_recieved += len(string)
                    f.write(string)

            s.send('ack'.encode())

            numOfFiles -= 1

############################################# User Handler #######################################################

    # Name:    options
    # Purpose: Allow user to use functions provided by the node
    # parem:   none
    # returns: none

    def options(self):
        while(self.consequence):  # change this to global etc etc explained above

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
        filename = input("enter filename: ")

        if os.path.isfile(filename):
            size = os.path.getsize(filename)
            file_key = self.hashery(filename)

            node = self.findSuccessor(str(file_key))

            user = node.split(' ')

            z = socket.socket()
            z.connect((self.ip, int(user[0])))
            toSend = 'store ' + filename + ' ' + str(size)
            z.send(toSend.encode())
            ack = z.recv(1024).decode()

            f = open(filename, 'rb')
            for chunk in iter(lambda: f.read(1024), b''):
                z.send(chunk)

            ack = z.recv(1024).decode()
            f.close()
            z.send('end'.encode())

        else:
            print("either file doesnot exist or is not in current directory")

    # Name:    GET
    # Purpose: Find the required file from the system using it's key.
    #          Contact the node with the file and get the file if exists
    # parem:   none
    # returns: none

    def GET(self):
        filename = input('name of file: ')
        hash_of_file = self.hashery(filename)

        node_with_file = self.findSuccessor(str(hash_of_file))
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
            filename = data[0]
            size = int(data[1])

            z.send('ack'.encode())

            string = z.recv(1024).decode()
            file = os.path.join(self.port, filename)

            if(not os.path.exists(self.port)):
                os.makedirs(self.port)

            f = open(file, "w+")
            total_recieved = len(string)
            f.write(string)
            while total_recieved < size:
                string = z.recv(1024).decode()
                total_recieved += len(string)
                f.write(string)

        z.send('end'.encode())

    # Name:    viewFiles
    # Purpose: Lets user view names of files stored at own node
    # parem:   none
    # returns: none

    def viewFiles(self):
        if(os.path.exists(self.port)):
            fileList = os.listdir(self.port)
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
        print("My Key : " + str(self.key))
        print("Pred Info " + str(self.predKey) + ' ' + str(self.predPort))
        print("suc of suc " + str(self.suc_suc_key) + ' '+str(self.suc_suc))
        print()
        print('Key | Port Num | value')
        print("-----------------------")
        for entry in self.fingerTable:
            if(entry.key % 10 == entry.key and entry.portNo % 10000 == entry.portNo):
                print('  ' + str(entry.key) + ' |   ' +
                      str(entry.portNo) + '   | ' + str(entry.value))
            elif(entry.key % 10 == entry.key):
                print('  ' + str(entry.key) + ' |   ' +
                      str(entry.portNo) + '  | ' + str(entry.value))
            elif(entry.portNo % 10000 == entry.portNo):
                print(' ' + str(entry.key) + ' |   ' +
                      str(entry.portNo) + '   | ' + str(entry.value))
            else:
                print(' ' + str(entry.key) + ' |  ' +
                      str(entry.portNo) + '   | ' + str(entry.value))
        print("-----------------------")

    # Name:    handleLogout
    # Purpose: called when user chooses to shut node down.
    #          informs other nodes its about to leave and sends
    #          its files to their successor
    # parem:   none
    # returns: none

    def handleLogout(self):
        # if only node in the DHT
        if(self.fingerTable[0].portNo == int(self.port)):
            self.consequence = False
            print("logging out")
            _thread.exit()

        self.logoutFileHandler()
        self.informPred()
        self.nodeLeft(
            self.port, self.fingerTable[0].portNo, self.fingerTable[0].key)

        # shuts down infinite loops in all three threads
        self.consequence = False

        # send one last request to self in case it is blocking
        try:
            z = socket.socket()
            z.connect((self.ip, int(self.port)))
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
        if(os.path.exists(self.port)):
            if(self.suc_unsure == True):
                time.sleep(6)

            # in every case, the node's successor will be the inheritor of the files
            try:
                z = socket.socket()
                z.connect((self.ip, int(self.fingerTable[0].portNo)))
            except:
                print('successor cannot be contacted')
                return

            file_list = os.listdir(self.port)

            for file in file_list:
                filename = os.path.join(self.port, file)
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
                # os.remove(filename)

            # os.rmdir(self.port)
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
            print('cannot contact predecessor')
            return

        toSend = 'your new successor ' + \
            str(self.fingerTable[0].portNo)
        z.send(toSend.encode())
        ack = z.recv(1024).decode()

        z.send('end'.encode())


############################################## Maintaining DHT ###################################################

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
                z.connect((self.ip, int(self.fingerTable[0].portNo)))

                z.send('hello'.encode())
                ans = z.recv(1024).decode()
                anssplit = ans.split(' ')

                self.suc_suc = int(anssplit[0])
                self.suc_suc_key = int(float(anssplit[1]))
                z.send('end'.encode())

            except:
                if(self.count < 1):
                    self.count += 1
                    self.suc_unsure = True

                else:
                    # successor needs to be updated as he is lost
                    self.nodeLeft(
                        self.fingerTable[0].portNo, self.suc_suc, self.suc_suc_key)

                    z = socket.socket()
                    z.connect((self.ip, int(self.suc_suc)))
                    toSend = 'I am new predecessor ' + \
                        self.port + ' ' + str(self.key)
                    z.send(toSend.encode())
                    ack = z.recv(1024).decode()
                    z.send('end'.encode())

                    self.count = 0
                    self.suc_unsure = False


############################################## Request Handler ###################################################

    # Name:    listener
    # Purpose: socket bound to address and port given at run time
    #          listening for any connections.
    # parem:   none
    # returns: none


    def listener(self):
        s = socket.socket()
        s.bind((self.ip, int(self.port)))
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
        while(True):
            string = peer.recv(1024).decode()
            string_in_list = string.split(' ')

            # edge case. no peer should be sending an empty string
            if(string == ''):
                _thread.exit()

            # Predecessor checking to see if alive
            if(string == 'hello'):
                toSend = str(self.fingerTable[0].portNo) + \
                    ' ' + str(self.fingerTable[0].key)
                peer.send(toSend.encode())

            # Predecessor announcing itself
            elif(string_in_list[0] == 'I'):
                if(string_in_list[3] == 'predecessor'):
                    self.predPort = int(string_in_list[4])
                    self.predKey = int(string_in_list[5])
                    peer.send('ack'.encode())

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
                ans = self.findSuccessor(string_in_list[1])
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
                self.predKey = int(string_in_list[2])
                self.predPort = int(string_in_list[1])
                peer.send('done'.encode())

            # a node has left the system
            elif(string_in_list[0] == 'nodeLeft'):
                ans = self.nodeLeft(int(string_in_list[1]), int(
                    string_in_list[2]), int(string_in_list[3]))
                peer.send(ans.encode())

            # peer wants to end the connection
            elif(string == 'end'):
                peer.close()
                _thread.exit()

    # Name:    store
    # Purpose: stores a file which another node sends
    # parem:   peer(socket object): socket object of the connecting node
    #          codeLine(string): message from peer containing filename and size
    # returns: none

    def store(self, peer, msg):
        linesplit = msg.split(' ')
        filename = ' '.join(linesplit[1:-1])
        size = int(linesplit[-1])

        peer.send('ack'.encode())

        file = os.path.join(self.port, filename)

        if(not os.path.exists(self.port)):
            os.makedirs(self.port)

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
        if(os.path.exists(self.port)):
            k = int(data[1])
            listOfFiles = os.listdir(self.port)
            toSend = list(
                filter((lambda x: self.hashery(x) <= k), listOfFiles))
            peer.send(str(len(toSend)).encode())
            ack = peer.recv(1024).decode()

            for filename in toSend:
                file = os.path.join(str(self.port), filename)
                toSend = filename + ' ' + str(os.path.getsize(file))
                peer.send(toSend.encode())
                ack = peer.recv(1024).decode()

                f = open(filename, 'rb')
                for chunk in iter(lambda: f.read(1024), b''):
                    peer.send(chunk)

                ack = peer.recv(1024).decode()

        else:
            peer.send('0'.encode())

    # Name:    upload
    # Purpose: sends requested file to connecting node
    # parem:   peer(socket object): socket object of the connecting node
    #          filename(string): name of file to send to connecting node
    # returns: none

    def upload(self, peer, filename):
        file = os.path.join(self.port, filename)
        if(os.path.exists(file)):
            size = os.path.getsize(file)

            toSend = filename + ' ' + str(size)
            peer.send(toSend.encode())
            ack = peer.recv(1024).decode()

            f = open(file, 'rb')
            for chunk in iter(lambda: f.read(1024), b''):
                peer.send(chunk)

        else:
            peer.send('file not found'.encode)

    # Name:    newJoinHandler
    # Purpose: updates it's fingertables with the new node if needed
    # parem:   pKey(string): key value of new node
    #          pPort(string): port num of new node
    # returns: none

    def newJoinHandler(self, pKey, pPort):
        iKey = int(pKey)
        iPort = int(pPort)
        print('new join: ', iKey, self.lastNewJoin)
        if (iKey == self.key or self.lastNewJoin == iKey):
            print('came to return')
            return
        else:
            print('came to work')
            self.lastNewJoin = iKey

            for entry in self.fingerTable:  # If your finger table needs to be updated

                if (iKey >= entry.value and iKey < entry.key):
                    entry.key = iKey
                    entry.portNo = iPort

                elif (entry.key < entry.value and iKey < entry.key):
                    entry.key = iKey
                    entry.portNo = iPort

                elif (entry.key < entry.value and iKey >= entry.value):
                    entry.key = iKey
                    entry.portNo = iPort

            for entry in self.fingerTable:
                if entry.key != iKey:
                    s = socket.socket()
                    s.connect((self.ip, entry.portNo))
                    toSend = 'newJoin ' + pKey + ' ' + pPort
                    s.send(toSend.encode())
                    temp = s.recv(1024).decode()
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

        toSend = 'I am new predecessor ' + str(self.port) + ' ' + str(self.key)
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

        finalHash = int(num % self.m)
        return finalHash

    # Name:    findSuccessor
    # Purpose: finds successor node of given key value
    # parem:   value (string): key value
    # returns: (string): port and key of successor node

    def findSuccessor(self, value):
        pKey = int(float(value))
        if (self.predKey < self.key and pKey > self.predKey and pKey < self.key):
            return str(self.port) + ' ' + str(self.key)
        elif (self.predKey > self.key and (pKey < self.key or pKey > self.predKey)):
            return str(self.port) + ' ' + str(self.key)
        availableKeys = []
        availableKeys.append(self.key)
        for entry in self.fingerTable:
            if entry.key not in availableKeys:
                availableKeys.append(entry.key)

        availableKeys.sort()

        for k in availableKeys:
            if k == pKey:
                return str(self.getPort(k)) + ' ' + str(k)

        if pKey > self.key:
            maxInRange = -1
            for k in availableKeys:
                if k > self.key and k < pKey and k != self.lastNewJoin and k > maxInRange:
                    maxInRange = k
            if maxInRange != -1:
                s = socket.socket()
                s.connect((self.ip, self.getPort(maxInRange)))
                toSend = 'findSuccessor ' + str(pKey)
                s.send(toSend.encode())
                returnVal = s.recv(1024).decode()
                s.send('end'.encode())
                return returnVal

        else:
            lowest = self.m+1
            for k in availableKeys:
                if k != self.key and k < lowest and k != self.lastNewJoin and k < pKey:
                    lowest = k

            if lowest != (self.m+1):
                s = socket.socket()
                s.connect((self.ip, self.getPort(lowest)))
                toSend = 'findSuccessor ' + str(pKey)
                s.send(toSend.encode())
                returnVal = s.recv(1024).decode()
                s.send('end'.encode())
                return returnVal

        # Take a decision if program reached here request can't be forwarded
        for i in range(0, len(availableKeys)):
            if availableKeys[i] > pKey:
                return str(self.getPort(availableKeys[i])) + ' ' + str(availableKeys[i])

        # return first value in available keys
        return str(self.getPort(availableKeys[0])) + ' ' + str(availableKeys[0])

    # Name:    getPort
    # Purpose: finds port number being used by node of a
    #          specific key value from it's fingertable
    # parem:   pKey (string): key value
    # returns: (int): port number of node

    def getPort(self, pKey):
        for entry in self.fingerTable:
            if entry.key == pKey:
                return entry.portNo

        if pKey == self.key:
            return self.port

        # error. no node found in fingertable with this key
        else:
            print("error: no node found corresponding to key in fingertable")
            return -1

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
            for entry in self.fingerTable:
                # connect to node and forward the request
                if entry.portNo != key:
                    s = socket.socket()
                    s.connect((self.ip, entry.portNo))
                    toSend = 'nodeLeft ' + \
                        str(key) + ' ' + str(sucPort) + ' ' + str(sucHashKey)
                    s.send(toSend.encode())
                    resp = s.recv(1024).decode()
                    s.send('end'.encode())

            if self.predPort != key:
                s = socket.socket()
                s.connect((self.ip, self.predPort))
                toSend = 'nodeLeft '+str(key) + ' ' + \
                    str(sucPort) + ' ' + str(sucHashKey)
                s.send(toSend.encode())
                resp = s.recv(1024).decode()
                s.send('end'.encode())

        # update your own fingerTable
            for entry in self.fingerTable:
                if entry.portNo == key:
                    entry.portNo = sucPort
                    entry.key = sucHashKey
            return 'updated'


def Main():
    if(len(sys.argv) == 3):  # additional node
        c = chord(sys.argv[1], sys.argv[2])

    elif(len(sys.argv) == 2):  # first node
        c = chord(sys.argv[1])

    else:
        print('for first node: python <filename> <portNum>')
        print('for any other node: python <filename> <portNum> <ReferencePortNum>')


if __name__ == '__main__':
    Main()
