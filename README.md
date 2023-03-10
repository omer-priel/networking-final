# Networking Final

At first, this is a final project of networking. \
The project contains 4 subprojects: app, client, dhcp and dns.

The app is server based RUDP for storage like FTP. The server support download, upload, list and delete requests. \
In addition, the clients can be anonymously or with user name and password.\
Client Help:

```terminal
client is CLI client for custom app like "FTP" based on UDP.
  client --help                                          - print the help content
  client [options] upload [--dest <destination>] <file / directory>  - upload file or directory
  client [options] download <remote file / directory> [destination]  - download file or directory
  client [options] list [remote directory] [--recursive] - print directory content
Options:
--user <user name>    - set user name
--password <password> - set user password, require --user
--host <host> - set the server host address, defualt: localhost
--port <port> - set the server port, defualt: 30034
--client-host <host> - set the client host address, defualt: localhost
--client-port <port> - set the client port, defualt: 20985
```

* TCP Mode: \
  In src/app/config.py you can change into TCP Mode (by defualt is false - UDP Mode) \
  In this mode the app and the client will use TCP. but they will act like is UDP and all the parts of the RUDP \
  will stay. Warrning this mode is only for the university - it will make the system slow!.

Other Sub-projects:

* The DHCP server are simple DHCP that based on only python and json file for saving the data.
* The DNS is a local DNS server that has static domains and caching recodes that saved in a json file.

## Folders Structure

* docs - Extra information
* profiles - Contains the profile.json
* res - Resources directory
* src - Source code
  * app - The application server
  * client - Client CLI for the application server
  * dhcp - The DHCP server
  * dns - The DNS server
  * lib - Shard lib for the other projects
  * scripts - For CI/CD
* storage - The servers storage directory
* temp - Temporary for tests
* uploads - Testing files and directories for the application
* LICENSE - The MIT LICENSE of the project
* Makefile - CI / CD and Testing scripts
* README - This README

## Requirements

Support linux OS only.

* python 3.10.x
* poetry

## Installation

Run the folow command in the terminal:

```bash
poetry config virtualenvs.in-project true
poetry install
```

## App - Client

### Description

This is server for storage files, the server and the client sending packets over the UDP. But,
same like TCP is reliable and optimize the network speed.

The pockets are divided into three layers, Base Layer, RUDP layer and FTP layer. When the FTP layer exists only in the first packets.
The flow, the client send request packet with the request fields (upload / download / list / delete) and the auth fields (anonymous, user name and password).
The server response with "ok" and error mesage if is not ok. In addition, it sends the size and the amount of segments. So, the client and the server be coordinated.

Then, the sender - client if "upload" and server if "download" or "list" sends the packet according to Cubic and the other side return with ACK until it get all the segments. If it is upload then the server sends Close packet. Else, the client send Download Complited until the server sends Close.

### Environment Variables

The Environment Variables will be declaerd in src/app/.env

| Name             | Description                           |
| ---------------- | ------------------------------------- |
| APP_HOST         | App host                              |
| APP_PORT         | App port                              |
| APP_STORAGE_PATH | Relative path of the strore directory |

### Get Started

Run for open command in the terminal for opening the app server:

```bash
make start-app
```

### Testing

At first, check that the server is running. after that run the folow commands in the terminal:

```bash
make test-client-help
make test-client-upload-all
make test-client-upload-10000
make test-client-upload-child-10000
make test-client-upload-range
make test-client-upload-user
make test-client-upload-user-multi
make test-client-upload-user-without-password

make test-client-download-all
make test-client-download-10000
make test-client-download-child-10000
make test-client-download-user
make test-client-download-user-without-password
make test-client-download-user-multi

make test-client-list
make test-client-list-recursive
make test-client-list-a
make test-client-list-a-c
make test-client-list-range
make test-client-list-user-multi
make test-client-list-user-without-password
make test-client-list-user-recursive

make test-client-delete-all
make test-client-delete-user
make test-client-delete-user-without-password
make test-client-delete-user-multi
make test-client-delete-root

make test-client-not-found
```

### Docs for development

Every Request / Response are made from Base Layer and the content layer

* Upload - Upload File / Directory
* Download - Download File / Directory
* List
* Delete - Delete File / Directory

#### RUDP Level

**Basic Layer**

|   Type  |  Sub Type  | Request ID |
|---------|------------|------------|
| 1 Bytes | 1 Bytes    | 8 Bytes    |

* Type:     type of RUDP layer
* Sub type: type of the application layer, the defualt is 0

*Request Layer*

| Full Pocket Size | Max Single Segment Size |
|------------------|-------------------------|
| 8 Bytes          | 8 Bytes                 |

| Anonymous | User Name Length |         User Name          | Password Length |         Password           |
|-----------|------------------|----------------------------|-----------------|----------------------------|
| 1 Byte    | 4 Bytes          | (User Name Length) * Bytes | 4 Bytes         | (User Name Length) * Bytes |

Type: 1

**Response Layer**

| OK      | Error Message Length |         Error Message          |
|---------|----------------------|--------------------------------|
| 1 Bytes | 1 Bytes              | (Error Message Length) * Bytes |

| Data Size | Segments Amount | Single Segment Size |
|-----------|-----------------|---------------------|
| 8 Bytes   | 8 Bytes         | 8 Bytes             |

Type: 2

* If Segments Amount is 0 then, not exists ACK's and Close pockets

**Ready For Downloading**

Type: 3

**Segment Layer**

| Segment ID | Segment Size |         Data         |
|------------|--------------|----------------------|
| 8 Bytes    | 8 Bytes      | Segment Size * Bytes |

Type: 4

**AKC Layer**

| Segment ID |
|------------|
| 8 Bytes    |

Type: 5

**Download Complited**

Type: 6

**Close**

Type: 7

#### FTP Level

**Upload Request Layer**

| Path Length |         Path          |
|-------------|-----------------------|
| 4 Bytes     | (Path Length) * Bytes |

Type: Request Layer
Path: path of file or directory on the server

The Uploaded Data: \
If the first byte is 1 then its file \
Else, if the first byte is 0 its a directory

* If exists file or directory, delete it
* Create the file / directory

**Download Request Layer**

| Path Length |         Path          |
|-------------|-----------------------|
| 4 Bytes     | (Path Length) * Bytes |

Type: Request Layer
Path: path of file or directory on the server

The Uploaded Data: \
If the first byte is 1 then its file \
Else, if the first byte is 0 its a directory

* Can't download file / directory that dos not exists

**List Request Layer**

| Path Length |         Path          | Recursive |
|-------------|-----------------------|-----------|
| 4 Bytes     | (Path Length) * Bytes | 1 Byte    |

Type: Request Layer
Path: path of the directory on the server

**List Data**

The full combine segments is: \
list of directories and files, when directory present

| Is Directory - 1 | Name Length |         Name          | Updated At |
|------------------|-------------|-----------------------|------------|
| 1 Byte           | 4 Bytes     | (Name Length) * Bytes | 8 Bytes    |

and file is

| Is Directory - 0 | Name Length |         Name          | Updated At | File Size  |
|------------------|-------------|-----------------------|------------|------------|
| 1 Byte           | 4 Bytes     | (Name Length) * Bytes | 8 Bytes    | 8 Bytes    |

**Delete Request Layer**

| Path Length |         Path          |
|-------------|-----------------------|
| 4 Bytes     | (Path Length) * Bytes |

Type: Request Layer
Path: path of file or directory on the server

**Delete Response Layer**

| Is File |
|---------|
| 1 Byte  |

Type: Request Layer

## DHCP Server

### Environment Variables

The Environment Variables will be declaerd in src/dhcp/.env

| Name          | Description                    |
| ------------- | ------------------------------ |
| SERVER_PORT   | DHCP port - 67                 |
| CLIENT_PORT   | DHCP port - 68                 |
| DATABASE_PATH | Relative path of the dhcp.json |

### Get Started

Run for open command in the terminal for opening the DHCP server:

```bash
make start-dhcp
```

### Config

Recive from port 67 and reply on port 68

dhcp.json fields:

* server_address - DHCP server IP Address
* network_interface - DHCP listening network interface
* lease_time - DHCP IP Address Lease Time in seconds
* renewal_time - DHCP Renewal Rime Time in seconds
* rebinding_time - DHCP Rebinding Time Time in seconds
* router -  The IP of the router / gateway
* subnet_mask - The subnet mask
* dns - IP of a DNS Server or null, this field is optional
* broadcast_address - IP for broadcasting or null, this field is optional
* pool_range - Range for the last part of the IP that the DHCP server returns
* ip_address_leases - All the leases that the server gives

### Testing

At first, check that the server is running. after that run the folow commands in the terminal:

```bash
ip a
sudo dhclient -r
ip a
sudo dhclient
ip a
sudo dhclient
ip a
sleep 40
ip a
sudo dhclient -r
ip a
sudo dhclient
ip a
sudo dhclient -r
ip a
```

### Docs for development

Description on the packets: \
The exists 6 types of packets in this server, and more that dos not used in this project. The \
types are: Discover, Offer, Request, ACK, NAK and Relese. \

## DNS Server

### Environment Variables

The Environment Variables will be declaerd in src/dns/.env

| Name          | Description                          |
| ------------- | ------------------------------------ |
| SERVER_PORT   | DNS port - 53                        |
| PARENT_PORT   | Port of the coonection to the parent |
| DATABASE_PATH | Relative path of the dns.json        |

### Get Started

Run for open command in the terminal for opening the DNS server:

```bash
make start-dns
```

### Config

Config: \
Recive from port 53

dns.json fields:

* parent_dns - IP Address of parent DNS server of this server
* static_ttl - The Time To Live in seconds for the domains of this server
* static_records - Static Records of this server, the key is the domain of the record
  * ip_address - IP Address of the domain
* cache_records - Cashed A Records, the key is the domain of the record
  * ip_address - IP Address of the domain
  * expired_time - When the record is expired in seconds

### Testing

At first, check that the server is running. after that run the folow commands in the terminal:

```bash
make test-dns-all
```

## Links

* Python Struct: <https://docs.python.org/3.7/library/struct.html>
* DHCP Wikipedia: <https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol>
* DHCP defied and who it works: <https://www.networkworld.com/article/3299438/dhcp-defined-and-how-it-works.html>
* DHCP Leases: <https://www.youtube.com/watch?v=5QhnovYb6yM>
* DNS Wikipedia: <https://en.wikipedia.org/wiki/Domain_Name_System>
* DNS RFC 1035: <https://www.ietf.org/rfc/rfc1035.txt>

## Author

* Omer Priel
* ...

## License

MIT
