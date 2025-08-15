"""Этот скрипт создает многосерийные видеоролики с использованием модели Veo 3.

Этот скрипт демонстрирует, как создать короткое видео или влог из идеи.
Он работает в три основных этапа:
1.  **Создание сцен**: на основе идеи он создает серию
    подсказок для сцен с использованием модели Gemini. Эти подсказки управляют созданием видео.
2.  **Создание видео**: для каждой подсказки сцены он вызывает модель Veo 3 для
    создания короткого видеоклипа.
3.  **Объединение видео**: он использует библиотеку MoviePy для объединения отдельных
    видеоклипов в одно окончательное видео.

Чтобы использовать этот скрипт, установите необходимые библиотеки:
    uv pip install moviepy google-genai pydantic

Затем запустите скрипт из своего терминала:
    python examples/veo3-generate-viral-vlogs.py
"""

import os
import time
from google import genai
from pydantic import BaseModel
from moviepy import VideoFileClip, concatenate_videoclips

client = genai.Client()


class Scene(BaseModel):
    description: str
    negative_description: str


class SceneResponse(BaseModel):
    scenes: list[Scene]


def generate_scenes(
    idea: str,
    character_description: str,
    character_characteristics: str = "саркастичный, драматичный, эмоциональный и привлекательный",
    number_of_scenes: int = 4,
    video_type: str = "видео",
    video_characteristics: str = "влогинг, реалистичный, 4k, кинематографический",
    camera_angle: str = "фронтальный",
    output_dir: str = "scenes",
) -> list[Scene]:
    """Создает описания сцен для видео на основе идеи.

    Args:
        idea: Основная концепция или тема видео.
        character_description: Визуальное описание главного героя.
        character_characteristics: Черты характера персонажа.
        number_of_scenes: Количество сцен для создания.
        video_type: Тип видео (например, «влог», «реклама»).
        video_characteristics: Общий стиль видео.
        camera_angle: Основной ракурс камеры.
        output_dir: Каталог для сохранения сгенерированных описаний сцен.

    Returns:
        Список объектов Scene, каждый из которых содержит описание для сцены.
    """
    os.makedirs(output_dir, exist_ok=True)
    single_scene_prompt = '''Вы — автор подсказок для кинематографических видео для Google Veo 3. Veo 3 — это усовершенствованная модель для создания видео с помощью искусственного интеллекта, которая преобразует текстовые или графические подсказки в видео высокой четкости, теперь с интегрированной возможностью встроенной генерации синхронизированного звука, включая диалоги, звуковые эффекты и музыку.

Ваша задача — создать серию отдельных подсказок для сцен для {video_type}. Эти подсказки будут использоваться для создания серии видеороликов, посвященных определенному персонажу и идее. Каждая подсказка должна представлять собой самодостаточное, подробное описание, которое четко инструктирует видеомодель о том, что нужно создать. Сцены должны быть короткими, визуальными, простыми, кинематографичными и иметь вариации в способах съемки. Описание персонажа и описание локаций должны быть согласованы во всех сценах.

**Основные входные данные:**
*   **Тема видео:** {idea}
*   **Описание главного героя:** {character_description}
*   **Личность персонажа:** {character_characteristics}
*   **Количество сцен для создания:** {number_of_scenes}
*   **Основной ракурс камеры:** {camera_angle}
*   **Общий стиль видео:** {video_characteristics}

---

**Инструкции и ограничения:**

1.  **Структура:** Создайте ровно {number_of_scenes} отдельных подсказок для сцен.
2.  **Длина сцены:** Каждая подсказка должна описывать действие или момент продолжительностью примерно 8 секунд.
3.  **Согласованность персонажа:** Основное визуальное описание главного героя должно быть включено и оставаться согласованным в каждой сцене.
    *   **ДА:** Если у персонажа в сцене 1 есть шрам над левым глазом, он должен быть у него во всех последующих сценах.
    *   **НЕТ:** Персонаж носит шляпу в одной сцене и не имеет шляпы в следующей без причины.
    *   **Руководство:** Чтобы обеспечить согласованность, сосредоточьтесь на легко воспроизводимых визуальных атрибутах. Простой текст на одежде (например, «CHAD»), сплошные цвета или отчетливые прически генерируются более надежно в разных сценах, чем сложные логотипы, замысловатые узоры или определенные лица.
4.  **Подробные визуальные эффекты:** Используйте яркий, конкретный язык.
    *   **ХОРОШО:** «Персонаж в белоснежной футболке с жирным черным текстом «CHAD», напечатанным на ней».
    *   **ПЛОХО:** «Персонаж в простой рубашке».
5.  **Согласованность местоположения:** Описание местоположения должно быть согласованным во всех сценах, если местоположение одинаковое.
6.  **Форматирование диалога:** Чтобы включить диалог, используйте формат: `[глагол, указывающий тон]: "[текст диалога]"`. Например: `спокойно говоря: "Все идет по плану"` или `крича: "Берегись!"`.
7.  **Вариация камеры:** Придерживаясь основного ракурса `{camera_angle}`, вводите вариации в типах кадров (например, крупный план, средний план, общий план, точка зрения), чтобы сделать сцены динамичными.
8.  **Интеграция стиля:** Описательный язык в ваших подсказках должен отражать желаемые `{video_characteristics}` (например, для стиля «кинематографический, угрюмый» используйте слова, которые вызывают тени, контраст и эмоции).
9.  **Самодостаточные подсказки:** Каждая подсказка для сцены должна быть написана от третьего лица и содержать всю необходимую информацию для того, чтобы видеомодель могла сгенерировать ее независимо.

---

**Формат вывода:**

Предоставьте вывод в виде одного допустимого объекта JSON. Объект должен содержать один ключ, `"scenes"`, который содержит список объектов сцен. Каждый объект сцены в списке должен строго соответствовать этой схеме:

```json
{{
  "scenes": [
    {{
      "description": "[тип кадра] [описание главного героя], который [описание действия и эмоции]. Место действия — [описание местоположения]. Персонаж [глагол, указывающий тон]: \"[текст диалога]\". Сцена снята с ракурса {camera_angle} в стиле {video_characteristics}.",
      "negative_description": "[Опишите элементы, которые нужно исключить из сцены]."
    }},
    {{
      "description": "...",
      "negative_description": "..."
    }}
  ]
}}
```

---

**Пример:**

**Входные данные:**
*   **Тема видео:** Домашний повар пробует до смешного острый перец.
*   **Описание главного героя:** Мужчина лет 20-ти.
*   **Количество сцен для создания:** 2
*   **Основной ракурс камеры:** Статичный средний план
*   **Общий стиль видео:** Яркий, высокой четкости, комедийный

**Сгенерированный вывод:**

```json
{{
  "scenes": [
    {{
      "description": "Крупный план Алекса, мужчины лет 20-ти с вьющимися каштановыми волосами и в очках, в синем фартуке поверх серой футболки. Он держит маленький, огненно-красный «Призрачный перец» и смотрит на него с притворной бравадой. Место действия — чистая, современная кухня. Он уверенно говорит: \"Это просто перец, насколько он может быть плохим?\". Сцена снята со статической камеры в ярком, комедийном стиле высокой четкости.",
      "negative_description": "Никаких других людей, никакой музыки."
    }},
    {{
      "description": "Средний план Алекса, мужчины лет 20-ти с вьющимися каштановыми волосами и в очках, в синем фартуке поверх серой футболки. Его лицо теперь ярко-красное, из глаз текут слезы, и он отчаянно обмахивает открытый рот. Место действия — та же современная кухня. Он кричит: \"ВОДЫ! ДАЙТЕ МНЕ ВОДЫ!\". Сцена снята со статической камеры в ярком, комедийном стиле высокой четкости.",
      "negative_description": "Без огня, не размыто."
    }}
  ]
}}
```
'''

    prompt = single_scene_prompt.format(
        idea=idea,
        character_description=character_description,
        character_characteristics=character_characteristics,
        number_of_scenes=number_of_scenes,
        camera_angle=camera_angle,
        video_type=video_type,
        video_characteristics=video_characteristics,
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=SceneResponse.model_json_schema(),
        ),
    )
    scenes = SceneResponse.model_validate_json(response.text).scenes

    with open(os.path.join(output_dir, "scenes.md"), "w") as f:
        for n, scene in enumerate(scenes):
            f.write(f"## Сцена {n+1}\n\n{scene.description}\n\n")

    return scenes


def generate_video(
    prompt: str,
    negative_prompt: str = None,
    aspect_ratio: str = "16:9",
    output_dir: str = "videos",
    fname: str = "video.mp4",
) -> str:
    """Создает один видеоклип из текстовой подсказки.

    Args:
        prompt: Текстовая подсказка, описывающая содержимое видео.
        negative_prompt: Описание того, чего следует избегать в видео.
        aspect_ratio: Соотношение сторон видео (например, «16:9»).
        output_dir: Каталог для сохранения сгенерированного видеофайла.
        fname: Имя файла для сохраненного видео.

    Returns:
        Путь к файлу сгенерированного видео.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, fname)

    video_rules = f'''Правила:
- Никаких субтитров или указаний камеры.
- Видео должно иметь соотношение сторон {aspect_ratio}.
- Делайте его коротким, визуальным, простым, кинематографичным.
'''

    # Generate video
    print(f"Создание видео в {aspect_ratio} из подсказки: {prompt[:100]}...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt + "\n\n" + video_rules,
        config=genai.types.GenerateVideosConfig(
            aspect_ratio="16:9",  # currently only 16:9 is supported
            person_generation="allow_all",
            negative_prompt=negative_prompt,
        ),
    )
    # Wait for videos to generate
    while not operation.done:
        print("Ожидание создания видео...")
        time.sleep(10)
        operation = client.operations.get(operation)

    for video in operation.response.generated_videos:
        client.files.download(file=video.video)
        video.video.save(path)

    return path


def merge_videos(
    video_files: list[str], output_file: str = "vlog.mp4", output_dir: str = "videos"
) -> str:
    """Объединяет несколько видеофайлов в один.

    Args:
        video_files: Список путей к видеофайлам для объединения.
        output_file: Имя файла для окончательного объединенного видео.
        output_dir: Каталог для сохранения окончательного видео.

    Returns:
        Путь к файлу объединенного видео.
    """
    os.makedirs(output_dir, exist_ok=True)
    # Load each video clip
    clips = [VideoFileClip(file) for file in video_files]

    # Concatenate the video clips
    final_clip = concatenate_videoclips(clips)

    # Write the final video file
    final_clip.write_videofile(
        os.path.join(output_dir, output_file),
        codec="libx264",
        audio_codec="aac",
    )

    return os.path.join(output_dir, output_file)


def generate_vlog(
    idea: str,
    character_description: str,
    character_characteristics: str = "саркастичный, драматичный, эмоциональный и привлекательный",
    video_type: str = "влог",
    video_characteristics: str = "реалистичный, 4k, кинематографический",
    camera_angle: str = "фронтальный, крупный план, средний план, дальний план",
    aspect_ratio: str = "16:9",
    number_of_scenes: int = 4,
    output_dir: str = "videos",
) -> None:
    """Создает полный влог с несколькими сценами.

    Эта функция организует весь процесс:
    1. Создает описания сцен.
    2. Создает видео для каждой сцены.
    3. Объединяет видео в окончательный влог.

    Args:
        idea: Основная концепция для влога.
        character_description: Описание главного героя.
        character_characteristics: Личность персонажа.
        video_type: Тип видео для создания.
        video_characteristics: Визуальный стиль влога.
        camera_angle: Ракурсы камеры для использования.
        aspect_ratio: Соотношение сторон окончательного видео.
        number_of_scenes: Количество сцен во влоге.
        output_dir: Каталог для сохранения всех сгенерированных файлов (сцен и видео).
    """
    os.makedirs(output_dir, exist_ok=True)

    scenes = generate_scenes(
        idea=idea,
        number_of_scenes=number_of_scenes,
        character_description=character_description,
        character_characteristics=character_characteristics,
        video_type=video_type,
        video_characteristics=video_characteristics,
        camera_angle=camera_angle,
        output_dir=output_dir,
    )

    video_files = []
    for n, scene in enumerate(scenes):
        video_file = generate_video(
            scene.description,
            negative_prompt=scene.negative_description,
            fname=f"video_{n}.mp4",
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
        )
        video_files.append(video_file)
    merge_videos(video_files, "vlog.mp4", output_dir=output_dir)


if __name__ == "__main__":
    generate_vlog(
        idea='''Турист в Лондоне осматривает все лучшие места''',
        character_description="Большой пушистый белый йети с черным лицом",
        character_characteristics="смешной",
        video_characteristics="реалистичный, 4k, высокое качество, влог",
        camera_angle="фронтальный, крупный план, говорящий в камеру",
        output_dir="yeti",
        number_of_scenes=4,
    )
