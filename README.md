# logdb
Log Research Database


This is both research project and a hobby project. It's not mature, it doesn't have appropriate quality and it's not production-grade!

Performance and security is not of a concern too.


## flow

```shell
./random-log.py 1000 > example.json
cd server
mkdir data
./index_log.py ../example.json data/example.sqlite
cd ../client
./query.py -f='CMP' example
```
