import random

import loguru


def generate_math_captcha(
        options_count: int = 6
) -> tuple[str, int, list[int]]:
    first_digit = random.randint(1, 10)
    second_digit = random.randint(1, 10)

    answer = first_digit + second_digit
    wrong_answers = set()
    while len(wrong_answers) < options_count - 1:
        wrong = answer + random.randint(-5, 5)

        if wrong != answer and wrong > 0:
            wrong_answers.add(wrong)

    options = list(wrong_answers) + [answer]
    random.shuffle(options)

    text = f"Сколько будет {first_digit} + {second_digit}?"

    return text, answer, options