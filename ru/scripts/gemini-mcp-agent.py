import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Получить ключ API Gemini из переменной окружения
api_key = os.environ.get("GEMINI_API_KEY")

# Создать экземпляр Gemini класса LLM
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro-exp-03-25",  # или "gemini-2.0-flash"
    temperature=0.7,
    max_retries=2,
    google_api_key=api_key,
)


async def main():
    async with MultiServerMCPClient(
        {
            "airbnb": {
                "command": "npx",
                "args": ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
                "transport": "stdio",
            },
            # Добавьте больше или свои собственные серверы здесь, работает также с удаленными серверами через sse
            # "weather": {
            #     "url": "http://localhost:8000/sse",  # Убедитесь, что сервер погоды запущен
            #     "transport": "sse",
            # },
        }
    ) as client:
        # Создать агент ReAct с серверами MCP
        graph = create_react_agent(model, client.get_tools())

        # Инициализировать историю разговоров, используя простые кортежи
        inputs = {"messages": []}

        print("Агент готов. Введите 'exit' для выхода.")
        while True:
            user_input = input("Вы: ")
            if user_input.lower() == "exit":
                print("Выход из чата.")
                break

            # Добавить сообщение пользователя в историю
            inputs["messages"].append(("user", user_input))

            # вызвать наш граф с потоковой передачей, чтобы увидеть шаги
            async for state in graph.astream(inputs, stream_mode="values"):
                last_message = state["messages"][-1]
                last_message.pretty_print()

            # обновить входные данные ответом агента
            inputs["messages"] == state["messages"]


if __name__ == "__main__":
    asyncio.run(main())
