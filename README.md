# Distributed-Hash-Table

This is a distributed network of nodes that allow its users to store and lookup any files in the system using a protocol inspired from [Chord](https://pdos.csail.mit.edu/papers/ton:chord/paper-ton.pdf).

Similar to chord, nodes in this DHT leverage a circular peer to peer distributed network to perform its function. This consists of different nodes arranged in a ring according to their assigned key and keeping track of all keys that fall under their keyspace. This keyspace is the range from the node's own key to it's predecessor's<sup>1</sup> key. For example if the node's key is 14 and it's predecessor's key is 8, then the node is responsible for keys 9 to 14.

<sup>1</sup> first node encountered when moving anti clockwise from node

[Figure 1](https://github.com/LAA225/Distributed-Hash-Table/blob/master/images/DHT1.png?raw=true)
This image is a visual example of what a working DHT looks like. Each dot on the circle represents a node with it's assigned key. Files indicated with squares are shown assigned to nodes according to their keys.

This arrangement allows for all nodes to distribute their loads efficiently and fairly among themselves. Yet be able to find the correct node for storing or looking up a file.

## Implementation

Each instance of the class _node_ in _dht.py_ serves as single node in the network. When run, a node needs the address<sup>2</sup> of any node currently online unless it is the first node in the network. It uses this reference node to find it's successor<sup>3</sup> and hence its rightful place in the DHT.

<sup>2</sup> In full scale each node would use both IP addresses and port numbers to connect to other nodes. However for demonstrative purposes, this dht runs locally with each node running as a seperate process using different port numbers to simulate the chord
<sup>3</sup> First node encountered moving clockwise from node

use fingertable with addresses of some nodes. enables functions completion in O(log n)

This DHT uses consistent hashing to distribute loads equally. # how files are stored and dealt with

.

## Usage

### PreRequisites

- Python 3.x

### Commands

To run first node:
`python dht.py <node port num>`

To run every other node:
` python dht.py <node port num> <port number of any online node>`
