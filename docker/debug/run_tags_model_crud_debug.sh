docker compose -f ../compose/docker-compose.ldap.yml -f ../compose/docker-compose.rabbitmq.yml -f compose/docker-compose.tags_model_crud.uvicorn.yml -f compose/docker-compose.tags_model_crud.debug.yml up --build -d
