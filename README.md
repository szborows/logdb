# logdb
Log Research Database

[![Build Status](https://travis-ci.com/szborows/logdb.svg?branch=master)](https://travis-ci.com/szborows/logdb)


This is both research project and a hobby project. It's not mature, it doesn't have appropriate quality and it's not production-grade!

Performance and security is not of a concern too. Ofc currently. The plan is to implement proper distribution and then optimize code working on a slave node.


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
* indices can be immutable up-front: no modification is supported after indexing a log. This can possibly cause problems when one wants to implement streaming logs, but purpose of this research DB is not real-time log indexing, but batch indexing and real-time querying.


## comparison with other databases

All not-distributed databases are outside of consideration.

| database | difference |
| --- | --- |
| Cassandra | Oriented around high write throughput. Although querying with CQL is effective when indices are well-designed, overall reading throughput is not primary concern in Cassandra and it doesn't work well with filtering (e.g. regex). |
| LogDevice | Based on Cassandra, so same characteristics apply. |
| ElasticSearch | AFAIK closest solution: good distribution and flexible querying mechanisms. However, performance is lower than possible and so-called deep scrolls are expensive. |
| PostgreSQL | Regex not part of standard. Poor distribution capabilities. |
| Redis | In-memory, so would not support storing lot of data. |
| rqlite | AFAIK it makes SQLite HA, so the data is duplicated on every node. -- tbd -- |
| Presto | -- tbd -- |
