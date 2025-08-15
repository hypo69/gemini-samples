"""
Агент браузера Gemini: Gemini 2.5 Flash может взаимодействовать и управлять веб-браузером с помощью browser_use.
"""

import os
import asyncio
import argparse
import logging  # Добавлено для ведения журнала
from browser_use.llm import ChatGoogle
from browser_use import (
    Agent,
    BrowserSession,
)

# # --- Настройка ведения журнала ---
# # При необходимости вы можете дополнительно настроить уровень ведения журнала
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s"
# )
# logger = logging.getLogger("GeminiBrowserAgent")
# # # При желании отключите шумные регистраторы
# # logging.getLogger("browser_use").setLevel(logging.WARNING)
# # logging.getLogger("playwright").setLevel(logging.WARNING)
# # --- Конец настройки ведения журнала ---


# ANSI цветовые коды
class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


async def setup_browser(headless: bool = False):
    """Инициализация и настройка браузера"""
    browser = BrowserSession(
        headless=headless,
        wait_for_network_idle_page_load_time=3.0,  # Увеличенное время ожидания
        highlight_elements=True,  # Оставляем подсветку для отладки в режиме с графическим интерфейсом
        # save_recording_path="./recordings", # Сохраняем запись, если необходимо
        viewport_expansion=500,  # Включаем элементы, находящиеся немного за пределами области просмотра
    )
    return browser


RECOVERY_PROMPT = """
ВАЖНОЕ ПРАВИЛО: если действие не удается выполнить несколько раз подряд (например, 3 раза) или если получаемый вами снимок экрана не меняется после 3 попыток,
НЕ повторяйте просто то же самое действие. 
Вместо этого используйте действие `go_back` и попробуйте перейти к цели другим способом. 
Если это не сработает, попробуйте другой поисковый запрос в Google.
"""

SUMMARIZER_PROMPT = """Вы — ассистент ИИ, специализирующийся на анализе и обобщении процессов. Ваша задача — прочитать данный текст, описывающий последовательность событий, и составить структурированное резюме предпринятых агентом шагов.

Ваше резюме должно в хронологическом порядке подробно описывать действия, наблюдения и решения агента, которые привели к конечному результату.

# Формат вывода:
Представьте резюме в виде нумерованного списка. Сгруппируйте шаги вместе. Каждая группа должна быть четко сформулирована и соответствовать этому строгому формату:

**Шаги [от - до]:**
- **Наблюдение:** Опишите, что агент видел, слышал или осознал на этих шагах.
- **Действие:** Опишите конкретное действие (действия), выполненное агентом.
- **Решение/Результат:** Объясните решение, принятое агентом на основе наблюдения, или непосредственный результат его действия.

# Контекст

{history}"""


async def agent_loop(llm, browser_session, query, initial_url=None):
    """Запуск цикла агента с необязательным начальным URL-адресом."""
    # Настройка начальных действий, если указан URL-адрес
    initial_actions = None
    if initial_url:
        initial_actions = [
            {"open_tab": {"url": initial_url}},
        ]

    agent = Agent(
        task=query,
        message_context="Имя пользователя — Филипп, и он живет в Нюрнберге. Сегодня 24.07.2025.",
        llm=llm,
        browser_session=browser_session,
        use_vision=True,
        generate_gif=True,
        initial_actions=initial_actions,
        extend_system_message=RECOVERY_PROMPT,
        max_failures=3,
    )
    # Запуск агента и браузера, передача перехватчика ведения журнала
    result_history = await agent.run()

    with open("history.md", "w") as f:
        history = "Это история всех шагов, предпринятых агентом для получения конечного результата."
        for h in result_history.history:
            # Безопасный доступ к метаданным и номеру шага
            metadata = getattr(h, "metadata", None)
            step_number = getattr(metadata, "step_number", "Н/Д")

            # Безопасный доступ к выводу модели и ходу мыслей
            model_output = getattr(h, "model_output", None)
            thinking = (
                getattr(model_output, "thinking", "Процесс мышления не записан.")
                or "Процесс мышления не записан."
            )
            memory = (
                getattr(model_output, "memory", "Память не записана.")
                or "Память не записана."
            )
            evaluation = (
                getattr(
                    model_output,
                    "evaluation_previous_goal",
                    "Оценка не записана.",
                )
                or "Оценка не записана."
            )

            # Безопасный доступ к результату и извлеченному содержимому
            result_list = getattr(h, "result", [])
            content_parts = []
            if result_list:
                for res in result_list:
                    extracted = getattr(res, "extracted_content", None)
                    if extracted:
                        content_parts.append(extracted)

            content = (
                "\n".join(content_parts) if content_parts else "Содержимое не извлечено."
            )

            history += f"""
# Шаг: {step_number}
## Мышление
{thinking}
## Оценка
{evaluation}
## Память
{memory}
## Результат
{content}

"""

        f.write(history)

        with open("summary.md", "w") as f:

            response = await llm.get_client().aio.models.generate_content(
                model=llm.model, contents=SUMMARIZER_PROMPT.format(history=history)
            )
            f.write(response.text)

    return result_history.final_result() if result_history else "Результат не найден"


async def main():
    # Отключить телеметрию
    os.environ["ANONYMIZED_TELEMETRY"] = "false"

    # --- Разбор аргументов ---
    parser = argparse.ArgumentParser(
        description="Запуск агента Gemini с взаимодействием с браузером."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash",
        help="Модель Gemini для использования в основных задачах.",
    )
    parser.add_argument(
        "--headless",
        default=False,
        # action="store_true",
        # help="Запуск браузера в безголовом режиме.",
    )
    args = parser.parse_args()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("GEMINI_API_KEY не найден в переменных окружения.")
        return

    llm = ChatGoogle(
        model=args.model,
        api_key=gemini_api_key,
        config={"automatic_function_calling": {"maximum_remote_calls": 100}},
    )
    browser = await setup_browser(headless=args.headless)

    print(f"{Colors.BOLD}{Colors.PURPLE}🤖 Агент браузера Gemini готов{Colors.RESET}")
    print(f"{Colors.GRAY}Введите 'exit' для выхода{Colors.RESET}\n")

    while True:
        try:
            # Получить ввод пользователя и проверить наличие команд выхода
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}Вы: {Colors.RESET} ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print(f"\n{Colors.GRAY}До свидания!{Colors.RESET}")
                break

            print(
                f"{Colors.BOLD}{Colors.GREEN}Gemini: {Colors.RESET}",
                end="",
                flush=True,
            )
            # Обработать подсказку и запустить цикл агента
            result = await agent_loop(llm, browser, user_input)

            # Отобразить окончательный результат
            print(f"{Colors.GREEN}{result}{Colors.RESET}\n")

        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except Exception as e:
            print(f"\nПроизошла ошибка: {e}")

    # Убедиться, что браузер закрыт правильно
    try:
        await browser.close()
        print("Браузер успешно закрыт.")
    except Exception as e:
        print(f"\nОшибка при закрытии браузера: {e}")


if __name__ == "__main__":
    # Убедиться, что цикл событий управляется правильно, особенно в интерактивном режиме
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nВыход из программы.")
