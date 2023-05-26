from src.common.model_crud_settings import ModelCRUDSettings

class TagsModelCRUDSettings(ModelCRUDSettings):
    #: имя сервиса. сервисы *_mod_crud создают в иерархии узел с таким же именем
    svc_name: str = "tags_model_crud"
    #: строка коннекта к RabbitMQ
    amqp_url: str = "amqp://prs:Peresvet21@rabbitmq/"
    #: строка коннекта к OpenLDAP
    ldap_url: str = "ldap://ldap:389/cn=prs????bindname=cn=admin%2ccn=prs,X-BINDPW=Peresvet21"

    #: обменник для публикаций
    pub_exchange: dict = {
        "name": "tags_model_crud",
        "type": "direct",
        "routing_key": "tags_model_crud"
    }

    #: обменник, который публикует запросы от API_CRUD
    api_crud_exchange: dict = {
        "name": "tags_api_crud",
        "type": "direct",
        "queue_name": "tags_api_crud",
        "routing_key": "tags_api_crud"
    }

    hierarchy: dict = {
        #: имя узла для хранения сущностей в иерархии
        #: если узел не требуется, то пустая строка
        "node": "tags",
        #: класс экзмепляров сущности в иерархии
        "class": "prsTag",
        #: список через запятую родительских классов
        "parent_classes": "prsObject",
        #: флаг создания узла ``cn=system`` внутри узла экземпляра сущности
        "create_sys_node": True
    }