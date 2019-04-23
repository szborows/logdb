#!/bin/bash

setup() {
    docker-compose up -d test_executor
}

teardown() {
    docker-compose down
}

test_health_immediate_startup() {
    docker-compose up -d server1 server2 server3
    assert "docker-compose exec test_executor /utils/wait_for_cluster"
}

test_health_late_peers_startup() {
    docker-compose up -d server1
    sleep 10s && docker-compose up -d server2 server3
    assert "docker-compose exec test_executor /utils/wait_for_cluster"
}
