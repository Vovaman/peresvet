# -f docker/compose/docker-compose.pgadmin.load_tests.yml \
docker compose \
-f docker/compose/docker-compose.ldap.load_tests.yml \
-f docker/compose/docker-compose.dataStorages.load_tests.yml \
-f docker/compose/docker-compose.rabbitmq.load_tests.yml \
-f docker/compose/docker-compose.tags.load_tests.yml \
-f docker/compose/docker-compose.postgresql.data_on_disk.yml \
-f docker/compose/docker-compose.locust.load_tests.get_data_psql.yml \
up