# Networking Final

Final project of networking

* The app will work like FTP on UDP. but, with only single client at one time.
* The DNS will save the routes in json file

## Get Started

TODO

## For Developers

Every Request / Response are made from Base Layer and the content layer

* Upload
* Download
* List

### RUDP Level

#### Basic Layer

|   Type  |  Sub Type  | Request ID |
|---------|------------|------------|
| 1 Bytes | 1 Bytes    | 8 Bytes    |

* Type:     type of RUDP layer
* Sub type: type of the application layer, the defualt is 0

#### Request Layer

| Full Pocket Size | Max Single Segment Size |
|------------------|-------------------------|
| 8 Bytes          | 8 Bytes                 |

| Anonymous | User Name Length |         User Name          | Password Length |         Password           |
|-----------|------------------|----------------------------|-----------------|----------------------------|
| 1 Byte    | 4 Bytes          | (User Name Length) * Bytes | 4 Bytes         | (User Name Length) * Bytes |

Type: 1

#### Response Layer

| OK      | Error Message Length |         Error Message          |
|---------|----------------------|--------------------------------|
| 1 Bytes | 1 Bytes              | (Error Message Length) * Bytes |

| Data Size | Segments Amount | Single Segment Size |
|-----------|-----------------|---------------------|
| 8 Bytes   | 8 Bytes         | 8 Bytes             |

Type: 2

* If Segments Amount is 0 then, not exists ACK's and Close pockets

#### Ready For Downloading

Type: 3

#### Segment Layer

| Segment ID | Segment Size |         Data         |
|------------|--------------|----------------------|
| 8 Bytes    | 8 Bytes      | Segment Size * Bytes |

Type: 4

#### AKC Layer

| Segment ID |
|------------|
| 8 Bytes    |

Type: 5

#### Download Complited

Type: 6

#### Close (FIN)

Type: 7

### FTP Level

#### Upload Request Layer

| Path Length |         Path          |
|-------------|-----------------------|
| 4 Bytes     | (Path Length) * Bytes |

Type: Request Layer
Path: path of the file on the server

* If the file exists, delete it
* Create the file

#### Download Request Layer

| Path Length |         Path          |
|-------------|-----------------------|
| 4 Bytes     | (Path Length) * Bytes |

Type: Request Layer
Path: path of the file on the server

* Can't download file that dos not exists

#### List Request Layer

| Path Length |         Path          | Recursive |
|-------------|-----------------------|-----------|
| 4 Bytes     | (Path Length) * Bytes | 1 Byte    |

Type: Request Layer
Path: path of the directory (folder) on the server

#### List Data

The full combine segments is: \
list of directories and files, when directory present

| Is Directory - 1 | Name Length |         Name          | Updated At |
|------------------|-------------|-----------------------|------------|
| 1 Byte           | 4 Bytes     | (Name Length) * Bytes | 8 Bytes    |

and file is

| Is Directory - 0 | Name Length |         Name          | Updated At | File Size  |
|------------------|-------------|-----------------------|------------|------------|
| 1 Byte           | 4 Bytes     | (Name Length) * Bytes | 8 Bytes    | 8 Bytes    |

### DHCP Server

Config: \
Get from port 67 and reply to port 68 \

Storage: \

* Subnet Mask - The local subnet mask
* Getway - The IP of the gateway
* DNS - IP to a DNS Server

* IP Scopes
* Taken IP's

## Links

* Python Struct: <https://docs.python.org/3.7/library/struct.html>
* DHCP Wikipedia: <https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol>
* DHCP defied and who it works: <https://www.networkworld.com/article/3299438/dhcp-defined-and-how-it-works.html>

## Author

Omer Priel

## License

MIT
