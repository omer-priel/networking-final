# Networking Final

Final project of networking

* The app is TFTP that is based on UDP
* The DNS will save the routes in json file

## Get Started

TODO

## For Developers

Custom FTP Packets:

### Upload File

| Packet Data |
|----------|:---------:|-----:|-----:|
| 1 (Type) | File Path | Size | Data |

### List Files

| Packet Data |
|----------|:--------------:|
| 2 (Type) | Directory Path |

### Download File

| Packet Data |
|----------|:---------:|
| 3 (Type) | File name |

## Author

Omer Priel

## License

MIT
