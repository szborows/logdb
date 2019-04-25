#!/bin/bash

setup() {
    docker-compose up -d
}

teardown() {
    docker-compose down
}

test_no_logs_without_upload() {
    docker-compose exec test_executor /utils/wait_for_cluster
    docker-compose exec test_executor logdb --logdb-url http://server1:8080 upload /logs/log1.json log01
    sleep 10s
    expected="10"
    result=`docker-compose exec test_executor logdb --logdb-url http://server1:8080 query log01 | wc -l`
    assert_equals "$expected" "$result"
    result=`docker-compose exec test_executor logdb --logdb-url http://server2:8080 query log01 | wc -l`
    assert_equals "$expected" "$result"
    result=`docker-compose exec test_executor logdb --logdb-url http://server3:8080 query log01 | wc -l`
    assert_equals "$expected" "$result"
    expected="4"
    result=`docker-compose exec test_executor logdb --logdb-url http://server1:8080 query -f 'CMP2' log01 | wc -l`
    assert_equals "$expected" "$result"
    result=`docker-compose exec test_executor logdb --logdb-url http://server2:8080 query -f 'CMP2' log01 | wc -l`
    assert_equals "$expected" "$result"
    result=`docker-compose exec test_executor logdb --logdb-url http://server3:8080 query -f 'CMP2' log01 | wc -l`
    assert_equals "$expected" "$result"
}
