# Distributed-Hash-Table
DHT (peer to peer) using chord protocol

This is a Distributed Hash table that leverages a peer to peer distributed network to perform a store and lookup service for its users. It consists of nodes arranged in a ring and using consistent hashing to maintain loads.

In an full scale each would use both IP addresses and port numbers to connect to other nodes. However for demonstrative purposes, this dht runs locally with each node running as a seperate process using different port numbers to simulate the chord.

## Usage
### PreRequisites
* Python 3.x

### Commands
To run first node:
``` python dht.py <node port num> ```

To run every other node:
``` python dht.py <node port num> <port number of any online node>```
