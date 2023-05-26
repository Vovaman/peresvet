# класс для работы с иерархией

import copy
from typing import Any, Tuple, List
import json

from uuid import uuid4, UUID

import ldap
import ldap.modlist
import ldap.dn
import ldapurl
from ldappool import ConnectionManager

CN_SCOPE_BASE = ldap.SCOPE_BASE
CN_SCOPE_ONELEVEL = ldap.SCOPE_ONELEVEL
CN_SCOPE_SUBTREE = ldap.SCOPE_SUBTREE

class Hierarchy:
    """Класс для работы с иерархической моделью.

    Args:

        url (str): URL для связи с ldap-сервером;
        pool_size (int, optional): размер пула коннектов. По умолчанию - 10.

    """

    def __init__(self, url: str, pool_size: int = 10):
        self.url : str = url
        self.pool_size : int = pool_size
        self._cm : ConnectionManager = None
        self._base : str = None

    async def _does_node_exist(self, node: str) -> bool:
        """Проверка существования узла с указанным id.

        Args:
            node (str): id проверяемого узла.

        Returns:
            bool: True - если узел существует, False - иначе.
        """

        with self._cm.connection() as conn:
                res = conn.search_s(base=self._base, scope=CN_SCOPE_SUBTREE,
                    filterstr=f"(entryUUID={node})",attrlist=['cn'])
                if not res:
                    return False

        return True

    async def get_node_dn(self, node: str = None) -> str:
        """Метод определяет DN узла в иерархии по переданному id и
        возвращает его.
        В случае, если base = None, то возвращается DN базового узла
        всей иерархии.

        Args:
            base (str, optional): id узла в форме UUID. По умолчанию - None.

        Returns:
            str: DN узла.

        """

        if not node:
            return self._base

        if self._is_node_id_uuid(node):
            with self._cm.connection() as conn:
                res = conn.search_s(base=self._base, scope=CN_SCOPE_SUBTREE,
                                filterstr=f"(entryUUID={node})",attrlist=['cn'])
                if not res:
                    raise ValueError(f"Узел {node} не найден.")

            return res[0][0]

    def _is_node_id_uuid(self, node: str) -> bool:
        """Проверка того, что идентификатор узла
        имеет формат UUID.

        Args:
            node (str): проверяемый идентификатор узла

        Returns:
            bool: True - идентификатор в правильной форме, False - иначе.

        """

        try:
            UUID(node)
        except ValueError:
            return False

        return True

    def connect(self) -> None:
        """Создание пула коннектов к lda-серверу.
        URL передаётся при создании нового экземпляра класса ``Hierarchy``.

        Количество попыток восстановления связи при разрыве - 10. Время
        между попытками - 0.3с.
        """

        ldap_url = ldapurl.LDAPUrl(self.url)

        self._cm = ConnectionManager(
            uri=f"ldap://{ldap_url.hostport}",
            bind=ldap_url.who,
            passwd=ldap_url.cred,
            size=self.pool_size,
            retry_max=10,
            retry_delay=0.3
        )

        self._base = ldap_url.dn

    @staticmethod
    def __form_filterstr(filter_attributes: dict) -> str:
        """Метод формирует из переданных данных строку фильтра для поиска узлов
        в иерархии

        Args:
            filter_attributes (dict): атрибуты со значениями, по которым
            строится фильтр.
            См. :py:func:`hierarchy.Hierarchy.search`

        Returns:
            str: строка фильтра
        """

        filterstr = ""
        for key, values in filter_attributes.items():
            sub_filter = ""
            for value in values:
                sub_filter = f"{sub_filter}({key}={value})"
            if filterstr:
                filterstr = f"{filterstr}(|{sub_filter})"
            else:
                filterstr = f"(|{sub_filter})"

        filterstr = f"(&{filterstr})"

        return filterstr

    #TODO: return not List, but one tuple, because it is a generator
    async def search(self, payload: dict) -> Tuple[str, str, dict] | None:
        """Метод-генератор поиска узлов и чтения их данных.

        Результат - массив кортежей. Каждый кортеж состоит из трёх элементов:
        `id` узла (entryUUID), `dn` узла, словарь из атрибутов и их значений.

        Args:
            payload(dict) -

                .. code:: json

                    {
                        "id": ["first_id", "n_id"],
                        "base": "base for search",
                        "deref": true,
                        "scope": 1,
                        "filter": {
                            "prsActive": [true],
                            "prsEntityType": [1]
                        },
                        "attributes": ["cn", "description"]
                        }
                    }

                * id
                    список идентификаторов узлов, данные по которым
                    необходимо получить; если присутствует, то не учитываются ключи
                    ``base``, ``scope``, ``attributes``; по умолчанию - None;
                * base
                    id (uuid) или dn базового узла, от которого
                    вести поиск;
                    в случае отстутствия поиск ведётся от корня иерархии; по
                    умолчанию - None;
                * deref
                    флаг разъименования ссылок; по умолчанию - False;
                    .. todo:: Реализовать поведение флага ``deref``.
                * scope
                    масштаб поиска; возможные значения:

                    * 0 - возвращает данные по одному, указанному в ``base`` узлу;
                    * 1 - поиск среди непосредственных потомков узла;
                    * 2 - поиск по всему дереву;

                * filter
                    данные для формирования фильтра поиска; ``filter``
                    представляет собой словарь, ключами в котором являются имена
                    атрибутов, а значениями - массивы значений; фильтр формируется
                    так: значения атрибутов из массивов объединяются операцией
                    ``или``, а сами ключи - операцией ``и``;
                    например, если ключ ``filter`` =

                    .. code:: json

                        {
                            "cn": ["first", "second"],
                            "prsEntityType": [2, 3]
                        }

                    то будет сформирована такая строка фильтра:
                    ``(&(|(cn=first)(cn=second))(|(prsEntityType=1)(prsEntityType=2)))``
                * attributes
                    список атрибутов, значения которых необходимо
                    вернуть; по умолчанию - ``['*']``


        Returns:
            List[Tuple]: [(id, dn, attributes)]
        """

        ids = payload.get("id")
        if ids:
            filterstr = Hierarchy.__form_filterstr({"entryUUID": ids})
        else:
            filterstr = Hierarchy.__form_filterstr(payload["filter"])

        base = payload.get("base")
        scope = payload.get("scope", CN_SCOPE_SUBTREE)
        deref = payload.get("deref", True)
        return_attributes = payload.get("attributes", ['*'])
        return_attributes.append('entryUUID')

        with self._cm.connection() as conn:

            old_deref = conn.deref

            if deref:
                conn.deref = ldap.DEREF_SEARCHING
            else:
                conn.deref = ldap.DEREF_NEVER

            node = await self.get_node_dn(base)

            res = conn.search_s(base=node, scope=scope,
                filterstr=filterstr, attrlist=return_attributes)

            for item in res:
                yield (item[1]['entryUUID'][0].decode(), item[0], {
                    key: [value.decode() for value in values] for key, values in item[1].items()
                })

            conn.deref = old_deref

        yield

    async def add(self, base: str = None, attr_vals: dict = None) -> str:
        """Добавление узла в иерархию.

        Args:
            base (str): None | id | dn узла-родителя
            attr_vals (dict): словарь со значениями атрибутов

        Returns:
            str: id нового узла
        """
        attrs = {}
        if attr_vals:
            attrs = {
            key: values if isinstance(values, list) else [values] for key, values in attr_vals.items()
        }

        if "objectClass" not in attrs.keys():
            attrs["objectClass"] = ["prsModelNode"]

        rename_node = False
        if not attrs.get("cn"):
            rename_node = True
            attrs["cn"] = [str(uuid4())]

        cn_bytes = ldap.dn.escape_dn_chars(attrs['cn'][0])
        base_dn = await self.get_node_dn(base)
        dn = f"cn={cn_bytes},{base_dn}"

        modlist = {}
        for key, values in attrs.items():
            modlist[key] = []
            for value in values:
                new_value = None
                if value:
                    if isinstance(value, bool):
                        if value:
                            new_value = 'TRUE'
                        else:
                            new_value = 'FALSE'
                    elif isinstance(value, (int, float)):
                        new_value = str(value)
                    elif isinstance(value, dict):
                        new_value = json.dumps(value, ensure_ascii=False)
                    else: # str
                        new_value = value

                    new_value = new_value.encode('utf-8')

                modlist[key].append(new_value)

        modlist = ldap.modlist.addModlist(modlist)

        with self._cm.connection() as conn:
            try:
                conn.add_s(dn, modlist)
            except ldap.ALREADY_EXISTS:
                return None

            res = conn.search_s(base=dn, scope=CN_SCOPE_BASE,
                               filterstr='(cn=*)',attrlist=['entryUUID'])
            new_id = res[0][1]['entryUUID'][0].decode()
            if rename_node:
                await self.modify(
                    node=new_id,
                    attr_vals={
                        "cn": [new_id]
                    })

            return new_id

    async def add_alias(self, parentId: str, aliased_object_id: str, alias_name: str) -> str:
        aliased_object_dn = self.get_node_dn(aliased_object_id)
        return await self.add(base=parentId, attr_vals={
            "objectClass": ["alias", "extensibleObject"],
            "aliasedObjectName": [aliased_object_dn],
            "cn": [alias_name]
        })

    async def modify(self, node: str, attr_vals: dict) -> str :
        """Метод изменяет атрибуты узла.
        В случае, если в изменяемых атрибутах присутствует cn (то есть узел
        переименовывается), то метод возвращает новый DN узла.

        Args:
            node (str): id изменяемого узла. По умолчанию - None.
            attr_vals (dict): словарь с новыми значениями атрибутов.

        Returns:
            str: новый DN узла в случае изменения атрибута ``cn``, иначе - None.
        """

        if not node:
            raise ValueError("Необходимо указать узел для изменения.")
        if not attr_vals:
            raise ValueError("Необходимо указать изменяемые атрибуты.")

        real_base = await self.get_node_dn(node)

        cn = attr_vals.pop("cn", None)

        attrs = {
            key: value if isinstance(value, list) else [value] for key, value in attr_vals.items()
        }
        attrs = {
            key:[v.encode("utf-8") if isinstance(v, str) else v for v in values] for key, values in attrs.items()
        }

        with self._cm.connection() as conn:
            res = conn.search_s(real_base, CN_SCOPE_BASE, None, [key for key in attrs.keys()])
            modlist = ldap.modlist.modifyModlist(res[0][1], attrs)
            conn.modify_s(real_base, modlist)

            if cn:
                res = conn.search_s(real_base, CN_SCOPE_BASE, None, ['entryUUID'])
                id_ = res[0][1]['entryUUID']

                if isinstance(cn, list):
                    cn = cn[0]
                new_rdn = f'cn={ldap.dn.escape_dn_chars(cn)}'
                conn.rename_s(real_base, new_rdn)

                res = conn.search_s(self._base, CN_SCOPE_SUBTREE, f'(entryUUID={id_})')

                return res[0][0]

    async def move(self, node: str, new_parent: str):
        """Метод перемещает узел по дереву.

        Args:
            node (str): id перемещаемого узла
            new_parent (str): id нового родительского узла
        """

        base_dn = await self.get_node_dn(node)
        new_parent_dn = await self.get_node_dn(new_parent)

        rdn = ldap.dn.explode_dn(base_dn,flags=ldap.DN_FORMAT_LDAPV3)[0]

        with self._cm.connection() as conn:
            conn.rename_s(base_dn, rdn, new_parent_dn)

    async def delete(self, node: str):
        """Метод удаляет из ерархии узел и всех его потомков.

        Args:
            node (str): id удаляемого узла.
        """
        if not node:
            raise ValueError('Нельзя удалять корневой узел иерархии')

        node_dn = await self.get_node_dn(node)

        with self._cm.connection() as conn:
            conn.delete_s(node_dn)

    async def get_parent(self, node: str) -> Tuple[str, str]:
        """Метод возвращает для узла ``node`` id(guid) и dn
        родительского узла.

        Args:

            node (str): id или dn узла, родителя которого необходимо найти.

        Returns:

            (str, str): id(guid) и dn родительского узла.

        """
        res_node = None
        try:
            UUID(node)
            with self._cm.connection() as conn:
                res = conn.search_s(base=self._base, scope=CN_SCOPE_SUBTREE,
                                filterstr=f"(entryUUID={node})",attrlist=['cn'])
                if not res:
                    raise ValueError(f"Узел {node} не найден.")

                res_node = res[0][0]

        except ValueError as ex:
            if not ldap.dn.is_dn(node):
                raise ValueError(
                    f"Строка {node} не является корректным идентификатором узла."
                ) from ex
            res_node = node

        rdns = ldap.explode_dn(res_node)
        p = ','.join(rdns[1:])
        if not p:
            return (None, None)

        with self._cm.connection() as conn:
            res = conn.search_s(base=p, scope=CN_SCOPE_ONELEVEL,
                attrlist=['entryUUID'])
            if not res:
                raise ValueError("Родительский узел не найден.")

        return (res[0][1]['entryUUID'][0].decode('utf-8'), res[0][0])

    async def get_node_class(self, node: str) -> str:
        """Возвращает класс узла

        Args:
            node (str): id узла

        Raises:
            ValueError: в случае отсутствия узла генерирует исключение

        Returns:
            str: значение атрибута objectClass (одно значение, исключая ``top``)
        """
        with self._cm.connection() as conn:
            res = conn.search_s(base=self._base, scope=CN_SCOPE_SUBTREE,
                filterstr=f"(entryUUID={node})",attrlist=['objectClass'])
            if not res:
                raise ValueError(f"Узел {node} не найден.")

            obj_classes = res[0][1]["objectClass"]
            obj_classes.remove(b'top')
            return obj_classes[0].decode()