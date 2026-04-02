import uuid

import loguru

from app.models.matrix import Matrix
from app.models.telegram_user import TelegramUser

from collections import OrderedDict, defaultdict


def get_sorted_objects_by_ids(
    objects: list[Matrix | TelegramUser],
    objects_ids: list[int | uuid.UUID],
):
    order_dict = defaultdict()
    objects_dict = defaultdict()
    sorted_objects = []

    for index, obj_id in enumerate(objects_ids):
        order_dict[index] = str(obj_id)

    for obj in objects:
        objects_dict[str(obj.id)] = obj

    for position, obj_id in order_dict.items():
        sorted_objects.append(objects_dict.get(str(obj_id)))

    return sorted_objects


def get_reversed_dict(dct: dict):
    keys = list(dct.keys())
    values = list(dct.values())

    return dict(zip(list(reversed(keys)), list(reversed(values))))
