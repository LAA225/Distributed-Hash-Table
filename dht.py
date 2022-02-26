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
    IPadd = '-1'
    value = -1

    def __init__(self, pKey, pPortNo, pIPadd):
        key = pKey
        portNo = pPortNo
        IPadd = pIPadd

    def __init__(self):
        key = -1
        portNo = '-1'
        IPadd = -1


class chord:
    predKey = 0
    predPort = 0
    fingerTable = []
    nextNodeP = 0
    nextNodeK = 0
    lastNewJoin = 0
    suc_suc = 0
    suc_suc_key = 0
    port = 0
    ip = '127.0.0.1'
    key = 0
    consequence = True
    m = 64
    count = 0
    suc_unsure = False
    lastLeft = 0

    def __init__(self, own_port, other_port=None):
        if other_port is None:
            # Since there is no reference node given, this is the only node in the chord.
            # Creates finger table with itself at every entry as it knows no other node

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

        else:  # not the first to join
            self.port = own_port
            self.key = self.hashery(own_port)

            self.connectToChord(other_port)
            self.createFingerTable(int(other_port))
            self.fileGet()

        self.mainController()

    def mainController(self):
        # listener allows the node to answer any incoming requests in the background
        # checkSuccessor pings the nodes in it's fingertable to see if they're still alive in the background
        # options is the UI that user has access to perform the functions available

        t1 = threading.Thread(target=self.options, args=())
        t2 = threading.Thread(target=self.listener, args=())
        t3 = threading.Thread(target=self.checkSuccessor, args=())

        t1.start()
        t2.start()
        t3.start()

    def fileGet(self):
        s = socket.socket()
        s.connect((self.ip, self.fingerTable[0].portNo))
        toSend = 'fileGet '+str(self.key)
        s.send(toSend.encode())
        numOfFiles = int(s.recv(1024).decode())
        s.send('ack'.encode())

        while(numOfFiles):
            fise = s.recv(1024).decode()
            flist = fise.split(' ')
            filename = flist[0]
            size = int(flist[1])
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

            numOfFiles -= 1

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

                with open(file, 'rb') as f:
                    string = f.read(1024)
                    peer.send(string)
                    while string != '':
                        string = f.read(1024)
                        peer.send(string)

                time.sleep(0.1)

        else:
            peer.send('0'.encode())

    def connectToChord(self, otherPort):
        z = socket.socket()
        z.connect((self.ip, int(otherPort)))
        toSend = 'findSuccessor ' + str(self.key)
        z.send(toSend.encode())

        ans = z.recv(1024).decode()
        ansSplit = ans.split(' ')
        self.nextNodeP = int(float(ansSplit[0]))
        self.nextNodeK = int(float(ansSplit[1]))
        z.send('end'.encode())

        t = socket.socket()
        t.connect((self.ip, self.nextNodeP))
        t.send('getPredInfo'.encode())

        ans = t.recv(1024).decode()
        nextPred = ans.split(' ')
        self.predKey = int(float(nextPred[1]))
        self.predPort = int(float(nextPred[0]))

        toSend = 'updatePred ' + str(self.port) + ' '+str(self.key)
        t.send(toSend.encode())
        dump = t.recv(1024).decode()
        t.send('end'.encode())

        s = socket.socket()
        s.connect((self.ip, self.nextNodeP))
        toSend = 'newJoin ' + str(self.key) + ' ' + str(self.port)
        s.send(toSend.encode())

        ans = s.recv(1024).decode()
        s.send('end'.encode())

        print("connectToChord returned")

    def createFingerTable(self, otherPort):
        print("In Create Finger Table")
        totalEntries = int(math.log2(self.m))  # change this to log of 64
        predictedEntries = []

        for i in range(0, totalEntries):
            predictedEntries.append((self.key+(2**i)) % self.m)

        tmpfingerTable = fingerTableEntry()
        tmpfingerTable.key = self.nextNodeK
        tmpfingerTable.portNo = self.nextNodeP
        tmpfingerTable.IPadd = self.ip
        tmpfingerTable.value = int(predictedEntries[0])
        self.fingerTable.append(tmpfingerTable)
        for i in range(1, totalEntries):
            s = socket.socket()
            print("Create Finger Table Value : " + str(i))
            s.connect((self.ip, self.nextNodeP))
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
        print("createFingerTable returned")

    def PUT(self):
        filename = input("enter filename: ")
        print()
        print(filename)
        print()

        if os.path.isfile(filename):
            size = os.path.getsize(filename)
            file_key = self.hashery(filename)

            to_send = self.findSuccessor(str(file_key))

            user = to_send.split(' ')

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

    def store(self, peer, line):
        linesplit = line.split(' ')
        filename = ' '.join(linesplit[1:-1])
        size = int(linesplit[-1])

        peer.send('ack'.encode())

        print()
        print(filename)
        print()
        # Current_Directory = os.getcwd()
        file = os.path.join(self.port, filename)  # self.port + "\\" + filename

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

            # Current_Directory = os.getcwd()
            # self.port + "\\" + filename
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

    def upload(self, peer, filename):
        file = os.path.join(self.port, filename)
        if(os.path.exists(file)):
            size = os.path.getsize(file)

            toSend = filename + ' ' + str(size)
            peer.send(toSend.encode())
            ack = peer.recv(1024).decode()

            with open(file, 'rb') as f:
                byteToSend = f.read(1024)
                peer.send(byteToSend)
                while byteToSend != "":
                    byteToSend = f.read(1024)
                    peer.send(byteToSend)

        else:
            peer.send('file not found'.encode)

    def viewFiles(self):
        if(os.path.exists(self.port)):
            print('\n files present: ')
            print(os.listdir(self.port))
            print("")

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
                print('store a file\n')
                self.PUT()
                print('\n file stored \n')
            elif choice == '2':
                print('find a file\n')
                self.GET()
                print('\n file got and stored \n')
            elif choice == '3':
                print('files stored here\n')
                self.viewFiles()
            elif choice == '4':
                self.printFingerTable()

            elif choice == '5':
                print("logout\n")
                # self.consequence = False
                z = socket.socket()
                z.connect((self.ip, int(self.port)))
                z.send('logout'.encode())
                self.consequence = False
            else:
                print("invalid choice\n")

    def newJoinHandler(self, pKey, pPort):
        iKey = int(pKey)
        iPort = int(pPort)

        if (iKey == self.key or self.lastNewJoin == iKey):
            return
        else:
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

            self.printFingerTable()
            for entry in self.fingerTable:
                if entry.key != iKey:
                    s = socket.socket()
                    s.connect((self.ip, entry.portNo))
                    toSend = 'newJoin ' + pKey + ' ' + pPort
                    s.send(toSend.encode())
                    temp = s.recv(1024).decode()
                    s.send('end'.encode())
            # send request to all in your finger table that new joined

    def printFingerTable(self):
        print("-----------------------")
        print("My Key : " + str(self.key))
        print("Pred Info " + str(self.predKey) + ' ' + str(self.predPort))
        print("suc of suc " + str(self.suc_suc_key) + ' '+str(self.suc_suc))
        for entry in self.fingerTable:
            print(str(entry.key) + ' ' +
                  str(entry.portNo) + ' ' + str(entry.value))
        print("-----------------------")

    def listener(self):
        s = socket.socket()
        s.bind((self.ip, int(self.port)))
        s.listen(10)

        while(self.consequence):
            peer, addr = s.accept()
            _thread.start_new_thread(self.dealer, (peer, addr))

    def dealer(self, peer, addr):
        while(True):
            string = peer.recv(1024).decode()
            string_in_list = string.split(' ')

            if(string == ''):
                _thread.exit()

            if(string == 'hello'):
                toSend = str(self.fingerTable[0].portNo) + \
                    ' ' + str(self.fingerTable[0].key)
                peer.send(toSend.encode())

            elif(string_in_list[0] == 'I'):
                if(string_in_list[3] == 'predecessor'):
                    self.predPort = int(string_in_list[4])
                    self.predKey = int(string_in_list[5])
                    peer.send('ack'.encode())

            elif (string_in_list[0] == 'newJoin'):
                self.newJoinHandler(string_in_list[1], string_in_list[2])
                peer.send('done'.encode())

            elif(string == 'successor?'):
                toSend = str(self.fingerTable[0].portNo) + \
                    ' ' + str(self.fingerTable[0].key)
                peer.send(toSend.encode())

            elif(string == 'logout'):
                print('handle sending files off etc and logout')
                self.logout()

            elif(string_in_list[0] == 'store'):
                self.store(peer, string)

            elif(string_in_list[0] == 'get'):
                self.upload(peer, string_in_list[1])

            elif(string_in_list[0] == 'fileGet'):
                self.fileSend(peer, string_in_list)

            elif (string_in_list[0] == 'findSuccessor'):
                ans = self.findSuccessor(string_in_list[1])
                peer.send(ans.encode())

            elif(string == 'getPredInfo'):
                # print("Getting Predecessor Info"
                ans = str(self.predPort) + ' ' + str(self.predKey)
                peer.send(ans.encode())

            elif(string_in_list[0] == 'your'):
                self.contactSuc(int(string_in_list[3], int(string_in_list[4])))

            elif(string_in_list[0] == 'updatePred'):
                # print("Getting Successor Info"
                self.predKey = int(string_in_list[2])
                self.predPort = int(string_in_list[1])
                peer.send('done'.encode())

            elif(string_in_list[0] == 'nodeLeft'):
                ans = self.nodeLeft(int(string_in_list[1]), int(
                    string_in_list[2]), int(string_in_list[3]))
                peer.send(ans.encode())

            elif(string == 'end'):
                peer.close()
                _thread.exit()
                break

    def contactSuc(self, suc_port, suc_key):
        s = socket.socket()
        s.connect((self.ip, suc_port))
        toSend = 'I am new predecessor '+str(self.port) + ' '+str(self.key)
        s.send(toSend.encode())
        ack = s.recv(1024).decode()
        s.send('end'.encode())

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
            # print(each + " %d %d" %(num, multiplier)

        finalHash = int(num % self.m)
        print("key: %d" % (finalHash))
        return finalHash

    def findSuccessor(self, t):
        print("findSuccessor of " + t)
        # create an array of all available keys to

        pKey = int(float(t))
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

    def getPort(self, pKey):
        for entry in self.fingerTable:
            if entry.key == pKey:
                return entry.portNo

        if pKey == self.key:
            return self.port

        else:
            print("Error in getPort")

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
                    print('successor needs to be updated as he is lost\n')

                    self.nodeLeft(
                        self.fingerTable[0].portNo, self.suc_suc, self.suc_suc_key)
                    z = socket.socket()
                    print(self.suc_suc)
                    z.connect((self.ip, int(self.suc_suc)))
                    toSend = 'I am new predecessor ' + \
                        self.port + ' ' + str(self.key)
                    z.send(toSend.encode())
                    ack = z.recv(1024).decode()
                    z.send('end'.encode())

                    self.count = 0
                    self.suc_unsure = False
                    # doesnot connect means successor has left
                    # when have fingertable, can go to any of the entries to find new successor

    def nodeLeft(self, key, sucKey, sucHashKey):

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
                        str(key) + ' ' + str(sucKey) + ' ' + str(sucHashKey)
                    s.send(toSend.encode())
                    resp = s.recv(1024).decode()
                    s.send('end'.encode())

            if self.predPort != key:
                s = socket.socket()
                s.connect((self.ip, self.predPort))
                toSend = 'nodeLeft '+str(key) + ' ' + \
                    str(sucKey) + ' ' + str(sucHashKey)
                s.send(toSend.encode())
                resp = s.recv(1024).decode()
                s.send('end'.encode())
        # update your own fingerTable

            for entry in self.fingerTable:
                if entry.portNo == key:
                    entry.portNo = sucKey
                    entry.key = sucHashKey
            return 'updated'

    def logout(self):
        # if the only node in the chord then no need to transfer any files
        if(self.fingerTable[0].portNo == self.port):
            return

        if(os.path.exists(self.port)):
            if(self.suc_unsure == False):
                z = socket.socket()
                z.connect((self.ip, int(self.fingerTable[0].portNo)))

                file_list = os.listdir(self.port)

                print("")
                print(file_list)
                print("")

                for file in file_list:
                    toSend = 'store ' + file + ' ' + str(os.path.getsize(file))
                    z.send(toSend.encode())
                    ack = z.recv(1024).decode()

                    filename = os.path.join(self.port, file)
                    with open(filename, 'rb') as f:
                        byteToSend = f.read(1024)
                        z.send(byteToSend)
                        while byteToSend != "":
                            byteToSend = f.read(1024)
                            z.send(byteToSend)
                        time.sleep(0.5)

                z.send('end'.encode())
                time.sleep(0.5)
                z = socket.socket()
                z.connect((self.ip, self.predPort))
                toSend = 'your new successor ' + \
                    str(self.fingerTable[0].portNo) + \
                    ' ' + str(self.fingerTable[0].key)
                z.send(toSend.encode())
                ack = z.recv(1024).decode()
                z.send('end'.encode())
                self.nodeLeft(
                    self.port, self.fingerTable[0].portNo, self.fingerTable.key)

            else:
                time.sleep(6)
                z = socket.socket()
                z.connect((self.ip, int(self.fingerTable[0].portNo)))
                for file in os.listdir(self.port):
                    toSend = 'store ' + file + ' ' + str(os.path.getsize(file))
                    z.send(toSend.encode())
                    ack = z.recv(1024).decode()

                    filename = os.path.join(self.port, file)
                    with open(filename, 'rb') as f:
                        byteToSend = f.read(1024)
                        z.send(byteToSend)
                        while byteToSend != "":
                            byteToSend = f.read(1024)
                            z.send(byteToSend)
                        time.sleep(0.5)

                z.send('end'.encode())
                time.sleep(0.5)
                z = socket.socket()
                z.connect((self.ip, self.predPort))
                toSend = 'your new successor ' + \
                    str(self.fingerTable[0].portNo) + \
                    ' ' + str(self.fingerTable[0].key)
                z.send(toSend.encode())
                ack = z.recv(1024).decode()
                z.send('end'.encode())
                self.nodeLeft(
                    self.port, self.fingerTable[0].portNo, self.fingerTable.key)


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
