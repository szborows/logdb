#!/bin/bash

setup() {
    docker-compose up -d
}

teardown() {
    docker-compose down
}

test_single_log_indexing() {
    docker-compose exec test_executor /utils/wait_for_cluster
    result=`docker-compose exec test_executor bash -c "logdb --logdb-url http://server1:8080 -o json logs | jq -Mjar 'length'"`
    assert_equals "0" "$result"
    docker-compose exec test_executor logdb --logdb-url http://server1:8080 upload /logs/log1.json log01
    result=`docker-compose exec test_executor bash -c "logdb --logdb-url http://server1:8080 -o json logs | jq -Mjar 'length'"`
    sleep 1s
    assert_equals "1" "$result"
    assert "docker-compose exec test_executor logdb --logdb-url http://server1:8080 query -f '00:01' log01 | grep '00:01'"
}
