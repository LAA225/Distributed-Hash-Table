# Distributed-Hash-Table

This is a distributed network of nodes that allow its users to store and lookup any files in the system using a protocol inspired from the paper [Chord: A Scalable Peer-to-peer Lookup Protocol for Internet Applications](https://pdos.csail.mit.edu/papers/ton:chord/paper-ton.pdf).

Similar to chord, nodes in this DHT leverage a circular peer to peer distributed network to perform its function. This consists of different nodes arranged in a ring according to their assigned key and keeping track of all keys that fall under their keyspace. This keyspace is the range from the node's own key to it's predecessor's[^1] key. For example if the node's key is 14 and it's predecessor's key is 8, then the node is responsible for keys 9 to 14.

![Figure 1](https://github.com/LAA225/Distributed-Hash-Table/blob/master/images/DHT1.png?raw=true)

This image (taken from referenced paper) is a visual example of what a working DHT looks like. Each dot on the circle represents a node with it's assigned key. Files indicated with squares are shown assigned to nodes according to their keys.

This arrangement allows for all nodes to find the correct node for storing or looking up a file. They do so using a fingertable which contains addresses corresponding to nodes responsible for some[^2] keys in the DHT. These fingertables allow nodes to find the node responsible for a keyspace directly or forward the request to the most appropriate node that can solve the problem for it. This enables all lookup and storage operations to be completed in O(log n)

![Figure 2](https://github.com/LAA225/Distributed-Hash-Table/blob/master/images/fingertable.png?raw=true)

This image (taken from referenced paper) is a visual example for how the fingertable stores nodes addresses corresponding to certain keys and use them for lookup.

Furthermore, the DHT also insures that all nodes have a fair and equal load. It does this by hashing the file to find a key that corresponds to a certain node. However, since the DHT is designed for new nodes to continuously join or leave, a traditional hashing scheme to find the node to store the file such as:
`node to store file = hash(file) % num of nodes`
will create a huge problem. Everytime a node leaves or joins, this calculation would have to be repeated for all files in the system as the total number of nodes would have changed. On top of this huge computation cost, this scheme would require that one node knows how many total nodes are in the system at all times. This can only be done be with a central controller which defeats the purpose of a peer to peer system or all nodes constantly exchanging information, which would again incur high computation costs.

To solve this the hash table makes use of consistent hashing where the hashing scheme is independant of the number of nodes in the system at any given time. It is instead focuses on where an entity belongs in a certain keyspace. Thereby the scheme used is 
```node to store file = hash(file) % keyspace```.
This allows files' hash to remain constant despite nodes joining or leaving the system. Some files do need to change hands but this limits it to O(K/N) where K is total number of files and N is total number of nodes.

Furthermore, the node arrangement is fault tolerant and can detect node failures and fix fingertables within 6 seconds. However, there is no redundancy implemented so if a node failure occurs, the files it holds go with it. Hence implementing redundancy is to be the target of later versions.

## Implementation

### Node Setup

Each instance of the class _node_ in _dht.py_ serves as single node in the network. When run, a node needs the address[^3] of any node currently online unless it is the first node in the network. It uses this reference node to find it's successor[^4] and hence its rightful place in the DHT.

Once a node has identified its successor, it formally joins the DHT and informs other nodes of it's existence. Which enables them to update their own fingertables. The node then is active and builds its own fingertable over time.

The node can now fulfill its main purpose: storing and looking up files.

### User Handler and Request Handler

Every node provides functionality to the user to:

- store a file
- lookup a file
- view files stored on the node
- view fingertable
- logout

Files are stored based on name provided by the user. Once file existence is confirmed, the node finds it's key and then the node responsible for it. It contacts the node using a socket and sends it the data necessary to store the file. Each node stores files it is responsible for in a directory[^5] named after it's own key.

To find a file, the user has to supply it's name along with it's extension. The node is then able to find it's corresponding key and the node that should be responsible for it. That node is then contacted for information on the file. If it exists, then is sent again through a socket connection and stored in a directory specified by the user.

The user can view the names of all files stored on their node using option three.

Fingertable details along with information about the node's key, predecessor and successor of successor are available using option four. The fingertable shows the address and key associated with certain keys as shown below.

![Figure 3](https://github.com/LAA225/Distributed-Hash-Table/blob/master/images/fingertableExample.PNG?raw=true)

Logout allows the node to go offline gracefully by sending all it's files to it's successor which is their rightful inheritor. It also informs its predecessor and successor of it's leaving so that the DHT arrangement can be smoothly updated.

### Maintaining DHT

The objective of this thread is to detect and handle any sudden node failure. Thereby maintaining the arrangement of the DHT at all times.

Each node is pinged by it's predecessor every two seconds to see if it is alive. The predecessor inquires after the node's successor which would be it's new successor in the event that the node fails.

If a node cannot cannot contact it's successor two times in a row, it declares it offline and announces it's successor's successor to be it's new successor. The rest of the nodes follow and update their fingertables.

In this version, the list of immediate succesors is limited to one so the DHT cannot handle two or more consecutive node failure. However if two or more than two non consecutive nodes fail, the system is able to recover.
In future versions, this list would grow to be able to handle a number of successive nodes failing.

## Usage

### PreRequisites

- Python 3.x

### Commands

Each node is to be run in a seperate terminal. The working directory needs to be where ever _dht.py_ is.

To run first node:
`python dht.py <node port num>`

To run every other node:
` python dht.py <node port num> <port number of any online node>`

[^1]: first node encountered when moving anti clockwise from node
[^2]: fingertables contain entries for keys x + 2<sup>i</sup> where x is the node's own key and i is integers 1,2,3,4...
[^3]: In full scale each node would use both IP addresses and port numbers to connect to other nodes. However for demonstrative purposes, this dht runs locally with each node running as a seperate process using different port numbers to simulate the chord. Later versions may incorporate both ip and port.
[^4]: First node encountered moving clockwise from node
[^5]: Despite being a folder a apart, no node can access another node's files. It is meant to replicate the effect of running a node on individual machines.
