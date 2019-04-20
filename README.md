# logdb
Log Research Database

[![Build Status](https://travis-ci.com/szborows/logdb.svg?branch=master)](https://travis-ci.com/szborows/logdb)


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

## database requirements

* fastest possible query (with regex filtering, label/tag constraints, time/row-number ranges, offset and size)
* fair indexing time
* good distribution
* high availability
* failover


## comparison with other databases

| database | difference |
| --- | --- |
| Cassandra | |
| LogDevice | |
| ElasticSearch | |
| SQL | |
| Redis | |
| rqlite | |
