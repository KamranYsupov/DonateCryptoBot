import uuid
from datetime import datetime
from typing import List

import loguru
from app.models.matrix import Matrix
from app.models.telegram_user import TelegramUser
from app.models.telegram_user import MatrixBuildType
from app.core.config import settings


def get_sorted_matrices(matrices, status_list):
    """Возвращает список матриц отфильтрованных по статусу и полю created_at"""
    status_order = {status: index for index, status in enumerate(status_list)}
    return sorted(
        matrices,
        key=lambda x: (status_order.get(x.status, len(status_list)), x.created_at),
    )


def get_matrices_length(matrices) -> int:
    length = 0
    for i in matrices.items():
        length += 1
        length += len(i[-1])

    return length


def get_matrices_list(matrices) -> tuple[list[Matrix], list[Matrix]]:
    first_level_matrices = []
    second_level_matrices = []
    for first_level_matrix in matrices.keys():
        first_level_matrices.append(uuid.UUID(first_level_matrix))

    for first_level_matrix in first_level_matrices:
        for second_level_matrix in matrices[str(first_level_matrix)]:
            second_level_matrices.append(uuid.UUID(second_level_matrix))

    return first_level_matrices, second_level_matrices


def find_first_level_matrix_id(
        matrix: Matrix,
        second_level_matrix_id: Matrix.id
) -> Matrix.id | None:
    for first_level_matrix_id, lst in matrix.matrices.items():
        if str(second_level_matrix_id) in lst:
            return uuid.UUID(first_level_matrix_id)

    return None


def get_archived_matrices(
        matrices: List[Matrix],
) -> List[Matrix]:

    archived_matrices = [
        matrix for matrix in matrices
        if get_matrices_length(matrix.matrices) == settings.matrix_max_length
    ]

    return archived_matrices


def get_active_matrices(
        matrices: List[Matrix],
) -> List[Matrix]:

    archived_matrices = [
        matrix for matrix in matrices
        if get_matrices_length(matrix.matrices) < settings.matrix_max_length
    ]

    return archived_matrices


def find_free_place_in_matrix(
        matrices: dict,
        level_length: int = settings.level_length
) -> list[str]:
    if len(matrices) < level_length:
        return []

    def process_level(nodes):
        next_nodes = []

        for node, path in nodes:
            if isinstance(node, dict):
                for key, value in node.items():
                    new_path = path + [key]

                    if isinstance(value, list):
                        if len(value) < level_length or any(x is None for x in value):
                            return new_path

                    if isinstance(value, dict) and len(value) < level_length:
                        return new_path

                    next_nodes.append((value, new_path))

        if next_nodes:
            return process_level(next_nodes)

        return []

    return process_level([(matrices, [])])


def insert_into_matrices(matrices: dict, path, level, value):
    current_level = matrices

    for key in path:
        current_level = current_level[key]

    target_level = current_level

    if len(target_level) == settings.level_length:
        return

    if isinstance(target_level, list):
        target_level.append(value)
        return


    if isinstance(target_level, dict):
        target_level[value] = {} if level < 4 else []


def get_matrix_telegram_usernames_key(matrix: Matrix) -> str:
    return f"{matrix.owner_id.hex} {matrix.id} {matrix.created_at}"


