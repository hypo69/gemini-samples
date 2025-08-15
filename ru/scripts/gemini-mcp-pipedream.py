# pip install google-genai fastmcp
# требует Python 3.13+
import os
import asyncio
import logging
from datetime import datetime
from google import genai
from uuid import uuid4
from fastmcp import Client

# Подавить все журналы
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("google").setLevel(logging.CRITICAL)
logging.getLogger("mcp").setLevel(logging.CRITICAL)
logging.getLogger("fastmcp").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)


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


# Создать экземпляр Gemini класса LLM
client = genai.Client()

mcp_client = Client(
    {
        "mcpServers": {
            "pipedream": {
                "transport": "http",
                "url": "https://remote.mcp.pipedream.net",
                "headers": {
                    # обратите внимание, если у вас нет учетных данных разработчика Pipedream, вы можете использовать временный, недолговечный токен для разработки
                    # это создаст для вас эфемерную учетную запись, которая будет удалена через короткое время.
                    # обратитесь к документации Pipedream для получения дополнительной информации: https://pipedream.com/docs/connect/mcp/developers
                    "Authorization": f"Bearer {os.environ.get('PIPEDREAM_API_KEY',f'devtok_{uuid4()}')}",
                    # смотрите здесь доступные приложения: https://pipedream.com/docs/connect/mcp/app-discovery
                    "x-pd-app-slug": "gmail, google_calendar",
                },
            }
        }
    }
)


async def run():
    async with mcp_client:
        config = genai.types.GenerateContentConfig(
            temperature=0,
            tools=[mcp_client.session],
            system_instruction=f"""Очень важно: часовой пояс пользователя — {datetime.now().strftime("%Z")}. Текущая дата — {datetime.now().strftime("%Y-%m-%d")}. 
Любые даты до этой — в прошлом, а любые даты после этой — в будущем. При работе с современными организациями/компаниями/людьми, и когда пользователь запрашивает «последние», «самые свежие», «сегодняшние» и т. д., не думайте, что ваши знания актуальны; 
Вы можете и должны говорить на любом языке, на котором вас просит говорить пользователь, или использовать язык пользователя.""",
        )

        print(f"{Colors.BOLD}{Colors.PURPLE}🤖 Агент Gemini MCP готов{Colors.RESET}")
        print(f"{Colors.GRAY}Введите 'exit' для выхода{Colors.RESET}\n")

        chat = client.aio.chats.create(model="gemini-2.5-flash", config=config)

        while True:
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}Вы: {Colors.RESET}")
            if user_input.lower() == "exit":
                print(f"\n{Colors.GRAY}До свидания!{Colors.RESET}")
                break

            response = await chat.send_message_stream(user_input)
            print(
                f"{Colors.BOLD}{Colors.GREEN}Gemini: {Colors.RESET}",
                end="",
                flush=True,
            )

            async for chunk in response:
                print(f"{Colors.GREEN}{chunk.text}{Colors.RESET}", end="", flush=True)
            print("\n")


if __name__ == "__main__":
    asyncio.run(run())
