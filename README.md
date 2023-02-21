# Networking Final

Final project of networking

* The app will work like FTP on UDP. but, with only single client at one time.
* The DNS will save the routes in json file

## Get Started

TODO

## For Developers

Every Request / Response are made from Base Layer and the content layer

* Upload
  Auth with Packet
* List
* Download

### RUDP Level

#### Basic Layer

|   Type  |  Sub Type  | Packet ID |
|---------|:-----------|:---------:|
| 1 Bytes | 1 Bytes    | 8 Bytes   |

* Type: of "network" layer
* Sub type: of application, the defualt is 0

#### Auth Layer

| Full Pocket Size | Max Single Segment Size | Max Window Timeout |
|-----------------:|:-----------------------:|:------------------:|
| 8 Bytes          | 8 Bytes                 | 8 Bytes            |

Type: 1

#### Auth Response Layer

| Segments Amount | Single Segment Size | Window Timeout |
|----------------:|:-------------------:|:--------------:|
| 8 Bytes         | 8 Bytes             | 8 Bytes        |

Type: 2

* If Segments Amount is 0 then, not exists ACK's and Close pockets

#### Segment Layer

| Segment ID |   Segment Length    |         Data         |
|-----------:|--------------------:|---------------------:|
| 8 Bytes    | 8 Bytes             | Segment Size * Bytes |

Type: 3

#### AKC Layer

| Segment ID |
|-----------:|
| 8 Bytes    |

Type: 4

#### Close (FIN)

Type: 5

### FTP Level

#### Upload Request Layer

| Path Length |         Path          | File Size |
|------------:|----------------------:|----------:|
| 4 Bytes     | (Path Length) * Bytes | 8 Bytes   |

Type: Auth Layer
Sub Type: 1
Path: path of the file on the server

* If the file exists, delete it
* Create the file
* Can't upload more then 256 files in directory

#### Upload Response Layer

| OK      | Error Message Length |         Error Message          |
|--------:|---------------------:|-------------------------------:|
| 1 Bytes | 1 Bytes              | (Error Message Length) * Bytes |

Type: Auth Response Layer
Sub Type: 2

### Upload Response Segment

Type: Segment Layer
Sub Type: 3
Data: segment of the file

#### Download Request Layer

| Path Length |         Path          |
|------------:|----------------------:|
| 4 Bytes     | (Path Length) * Bytes |

Type: Auth Layer
Sub Type: 4
Path: path of the file on the server

* Can't download file that dos not exists

#### Download Response Layer

| OK      | Error Message Length |         Error Message          | File Size | Updated At |
|--------:|---------------------:|-------------------------------:|----------:|-----------:|
| 1 Bytes | 1 Bytes              | (Error Message Length) * Bytes | 8 Bytes   | 8 Bytes    |
Type: Auth Response Layer
Sub Type: 5

### Download Ready For Downloading

Type: AKC Layer
Sub Type: 6

### Download Response Segment

Type: Segment Layer
Sub Type: 7
Data: segment of the file

### Download Complited

Type: AKC Layer
Sub Type: 8

#### List Request Layer

| Path Length |         Path          |
|------------:|----------------------:|
| 4 Bytes     | (Path Length) * Bytes |

Type: Auth Layer
Sub Type: 9
Path: path of the directory (folder) on the server

#### List Response Layer

Head

|  Files Count |
|-------------:|
| 8 Bytes      |

File Row

| File Name Size |        File Name         | File Size | Updated At |
|---------------:|-------------------------:|----------:|-----------:|
| 4 Bytes        | (File Name Size) * Bytes | 8 Bytes   | 8 Bytes    |

Type: Auth Response Layer
Sub Type: 10

## Author

Omer Priel

## License

MIT
