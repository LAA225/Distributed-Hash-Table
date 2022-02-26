chord.py
made by Laiba Abid 20100099 and Dilawer Ahmed 20100177

features:
- nodes can join to form a DHT
- this is done by using the unique port and ip of every user to hash into a unique key
- this key is their place in the chord
- when a node joins, it is given the port number of an online node.
- it uses this to find it's successor.
- after being integrated into the chord, it is open to connections.
- furthermore failure resiliance has been implemented. if a node dies, then the chord can adjust again to form a 
  complete ring

code implementation:
- A class called chord has been implemented.
- it stores the Successor, Predecessor and Successor of Successor as variables along with respective keys.
- an object is created using the port number/numbers provided.
- the constructor initializes the node. (finding key, finding successor, finding predecessor)
- when a node finds it's successor, it contacts it and tells it that it is his new predecessor and asks for his old
  one. the node then contacts this old predecessor and tells it that it is it's new successor. thus this is updated.
- then three threads are started. (listener: which is listening for connections, options: asks the user what they 
  want to do, check_Successor: which connects with successor every 3 seconds to see if node still alive. this also updates Successor of Successor)

