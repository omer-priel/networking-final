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

### Network Level

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

| Segment ID |
|-----------:|
| 8 Bytes    |

Type: 3

#### AKC Response Layer

| Segment ID |
|-----------:|
| 8 Bytes    |

Type: 4

#### Close Response Layer

Type: 5

### FTP Level

#### Upload File Request

| File Path | File Size |
|:---------:|----------:|
| 255 Bytes | 8 Bytes   |

Type: Auth Layer
Sub Type: 1

* If the file exists, delete it
* Create the file
* Can't upload more then 256 files in directory

#### Upload File Response

| OK      | Error Message |
|--------:|--------------:|
| 1 Bytes | 255 Bytes     |

Type: Auth Response Layer
Sub Type: 2

### Upload File Response Segment

|       Data        |
|------------------:|
| File Size * Bytes |

Type: Segment Layer
Sub Type: 3

#### List Request

| Directory Path |
|---------------:|
| 255 Bytes      |

Type: Auth Layer
Sub Type: 4

#### List Response

Head

| File Path |  Files Count |
|----------:|-------------:|
| 255 Bytes | 8 Bytes      |

File Part

| File Name | File Size | Upload Date |
|----------:|----------:|------------:|
| 255 Bytes | 8 Bytes   | 8 Bytes     |

Type: Auth Response Layer
Sub Type: 5

#### Download File Request

| File name |
|----------:|
| 255 Bytes |

Type: Auth Layer
Sub Type: 6

* Can't download file that dos not exists

#### Download File Response

| File Name | File Size | Upload Date |
|----------:|----------:|------------:|
| 255 Bytes | 8 Bytes   | 8 Bytes     |

Type: Auth Response Layer
Sub Type: 7

### Download File Response Segment

|       Data        |
|------------------:|
| File Size * Bytes |

Type: Segment Layer
Sub Type: 8

## Author

Omer Priel

## License

MIT
