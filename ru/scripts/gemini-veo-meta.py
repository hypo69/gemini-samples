"""Этот скрипт создает многосерийные видеоролики с использованием модели Veo 3.

Этот скрипт демонстрирует, как создать короткое видео или влог из идеи.
Он работает в 5 основных этапов:
1. На основе идеи он генерирует серию подсказок для сцен с использованием Gemini 2.5.
2. Генерирует изображение на основе первой сцены с использованием Imagen 3
3. Для каждой подсказки сцены Veo 3 (быстрый) генерирует видеоклип.
4. Использует редактирование изображений Gemini 2.0, чтобы убедиться, что начальные изображения соответствуют сценам
5. Объедините отдельные видеоклипы в одно окончательное видео с помощью MoviePy

Чтобы использовать этот скрипт, установите необходимые библиотеки:
    uv pip install pillow google-genai pydantic moviepy

Затем запустите скрипт из своего терминала:
    python examples/gemini-veo-meta.py
"""

# pip install pillow google-genai pydantic moviepy

from io import BytesIO
import json
import os
import re
import time
from google import genai
from google.genai import types
from pydantic import BaseModel
from moviepy import VideoFileClip, concatenate_videoclips
from PIL import Image
import logging

# Настройте ведение журнала для отображения информации из этого скрипта и предупреждений от других.
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = genai.Client()

import pydantic
from typing import List, Optional

# Основные типы для проверки
from pydantic import BaseModel, Field, AnyUrl


class Shot(BaseModel):
    """Технические детали камеры для определенного клипа."""

    composition: str = Field(
        ...,
        description="Как выстроен кадр и какой объектив используется. Примеры: «Средний крупный план, объектив 35 мм, глубокий фокус, плавный подвес», «Экстремально широкий кадр, объектив 14 мм, установочный кадр с дрона с медленным раскрытием», «Голландский угол, портретный объектив 85 мм, ручная съемка с преднамеренным дрожанием камеры», «Кадр из-за плеча, объектив 50 мм, малая глубина резкости». ")
    camera_motion: str = Field(
        None,
        description="Описывает движение камеры во время съемки. Примеры: «медленный наезд на 60 см», «быстрый кадр со слежением за объектом», «статичный кадр со штатива без движения», «плавное движение крана с низкой до высокой точки», «ручной наезд с небольшим дрожанием», «круговое движение тележки вокруг объекта». ")
    frame_rate: str = Field(
        "24 кадра/с",
        description="Кадров в секунду, определяющих вид движения (24 кадра/с — кинематографический). Примеры: «24 кадра/с», «60 кадров/с для эффекта замедленного движения», «120 кадров/с для экстремального замедленного движения», «12 кадров/с для винтажного или покадрового эффекта». ")
    film_grain: float = Field(
        None,
        description="Добавляет стилистический эффект зернистости пленки (0=нет, более высокие значения=больше зернистости). Примеры: 0.05, 0.15, 0.0, 0.3." ")
    camera: str = Field(
        ...,
        description="Объектив камеры, тип кадра и стиль оборудования для этого клипа. Примеры: «плавный подвес 35 мм», «ручной iPhone с анаморфотным адаптером объектива», «камера RED на риге Steadicam», «винтажная 16-мм кинопленка с простым объективом». ")


class Subject(BaseModel):
    """Описывает внешний вид и гардероб персонажа в определенном клипе."""

    description: str = Field(
        ...,
        description="Полная, описательная подсказка персонажа для этого кадра. Примеры: «Никс Сайфер — 27 лет, 173 см, подтянутое спортивное телосложение; темно-бронзовая кожа, блестящая от воды; иссиня-черные зачесанные назад волосы; миндалевидные карие глаза за зеркальными солнцезащитными очками; маленькая татуировка в виде звезды за правым ухом; одета в бикини цвета металлического коралла и золотые серьги-кольца», «Маркус Чен — 45-летний шеф-повар, 180 см, крепкого телосложения; обветренные руки от многолетней готовки; борода с проседью; теплые карие глаза с морщинками смеха; одет в безупречный белый поварской китель с закатанными рукавами», «Луна-7 — нестареющий андроид, выглядящий на 25 лет, 165 см, изящное синтетическое телосложение; люминесцентная бледно-голубая кожа с узорами микросхем; хромированно-серебряные волосы в геометрическом бобе; фиолетовые светодиодные глаза; одета в облегающий матовый черный боди со светящимися акцентами». ")
    wardrobe: str = Field(
        ...,
        description="Конкретный наряд, надетый в этом клипе. Это может быть основано на default_outfit персонажа. Примеры: «бикини цвета металлического коралла, зеркальные солнцезащитные очки, золотые серьги-кольца», «потертая кожаная куртка, рваные джинсы, армейские ботинки, перчатки без пальцев», «струящееся изумрудное шелковое платье с замысловатой вышивкой бисером, бриллиантовая тиара», «тактическое снаряжение с кевларовым жилетом, ремнем с подсумками, очками ночного видения». ")


class Scene(BaseModel):
    """Описывает обстановку и окружение клипа."""

    location: str = Field(
        ...,
        description="Физическое место, где происходит сцена. Примеры: «бассейн-инфинити на крыше с видом на неоново-тропический городской пейзаж», «заброшенный викторианский особняк с заросшим плющом и разбитыми окнами», «шумный уличный рынок в Токио во время сезона цветения сакуры», «подпольный бар с тусклым освещением и джазовой атмосферой». ")
    time_of_day: str = Field(
        "полдень",
        description="Время суток, которое сильно влияет на освещение. Примеры: «полдень», «золотой час перед закатом», «синий час в сумерках», «глухая ночь только при лунном свете», «раннее утро с мягким рассветным светом», «пасмурный день». ")
    environment: str = Field(
        ...,
        description="Конкретные детали об окружении. Примеры: «освещенная солнцем вода в бассейне, отражающая меняющиеся узоры; плавающие надувные знаки доллара», «сильный дождь, создающий лужи, отражающие неоновые вывески; пар, поднимающийся из люков», «мягкий снегопад, скапливающийся на подоконниках; теплый свет, льющийся из уютных окон», «пустынный ветер, поднимающий облака песка; далекие молнии, освещающие силуэты кактусов». ")


class VisualDetails(BaseModel):
    """Описывает действия и реквизит в клипе."""

    action: str = Field(
        ...,
        description="Что персонаж физически делает в сцене. Примеры: «Никс опирается на край бассейна и на четвертый такт кокетливо машет рукой в сторону камеры, пока капли сверкают в воздухе», «Маркус осторожно выкладывает микрозелень пинцетом, каждое движение точное и обдуманное», «Луна-7 взаимодействует с голографическим дисплеем, ее пальцы танцуют в плавающих потоках данных», «персонаж паркурит по крышам, плавно перепрыгивая между зданиями». ")
    props: str = Field(
        None,
        description="Объекты, которые появляются или с которыми взаимодействуют в сцене. Примеры: «плавающие надувные знаки доллара», «антикварный латунный телескоп, направленный на звездное небо», «голографические шахматы с фигурами, которые светятся и парят», «винтажный мотоцикл с хромированными деталями и кожаными седельными сумками». ")


class Cinematography(BaseModel):
    """Определяет художественный визуальный стиль для этого клипа."""

    lighting: str = Field(
        ...,
        description="Конкретное направление освещения для этого кадра. Примеры: «высокоключевой полуденный солнечный свет с зеркальными бликами на мокрой коже», «драматическое освещение в стиле кьяроскуро с глубокими тенями и яркими бликами», «мягкий свет из окна с прозрачными занавесками, создающими пестрые узоры», «ночная сцена с неоновым освещением с красочными отражениями на мокром асфальте», «интерьер при свечах с теплой, мерцающей атмосферой». ")
    tone: str = Field(
        ...,
        description="Предполагаемое настроение и ощущение клипа. Примеры: «яркий, игривый, уверенный», «темный, напряженный и таинственный», «теплый, ностальгический и сентиментальный», «эфирный, сказочный и сюрреалистичный», «суровый, интенсивный и необработанный». ")
    color_grade: str = Field(
        ...,
        description="Цветокоррекция и настроение для этого клипа. Примеры: «гипернасыщенный неоново-тропический (ярко-розовый, аква, мандариновый)», «обесцвеченный, суровый и в холодных тонах для нуарного вида», «теплые, золотистые тона для вызова ностальгии», «высококонтрастный черно-белый с выборочными цветовыми акцентами», «цветовая схема блокбастера в бирюзовых и оранжевых тонах». ")


class AudioTrack(BaseModel):
    """Определяет звуковые элементы, специфичные для этого клипа."""

    lyrics: Optional[str] = Field(
        None,
        description="Текст песни, который будет синхронизирован с губами или услышан. Примеры: «Splash-cash, bling-blap—pool water pshh! Charts skrrt! like my wave, hot tropics whoosh!», «В тишине древних залов раздаются шепоты забытых душ», «Танцуя в неоновых огнях, город никогда не спит по ночам», «Разрывая цепи вчерашнего дня, находя силы уйти». ")
    emotion: Optional[str] = Field(
        None,
        description="Эмоциональный тон вокального исполнения. Примеры: «уверенный, ироничный», «мрачный и меланхоличный», «энергичный и радостный», «пронзительный и эфирный», «агрессивный и вызывающий», «нежный и уязвимый». ")
    flow: Optional[str] = Field(
        None,
        description="Ритм и каденция лирической подачи (особенно для рэпа). Примеры: «двойное время для первой строфы, краткий тег в половинном темпе», «медленный, в стиле разговорной речи с драматическими паузами», «мелодичный и напевный с плавными переходами», «стаккато, быстрая подача», «синкопированный ритм с акцентом на слабую долю». ")
    wave_download_url: Optional[AnyUrl] = Field(
        None,
        description="URL-адрес существующего аудиофайла для этого клипа (если доступно). ")
    youtube_reference: Optional[AnyUrl] = Field(
        None,
        description="URL-адрес видео на YouTube в качестве справки по стилю или содержанию." ")
    audio_base64: Optional[str] = Field(
        None,
        description="Строка аудиоданных в кодировке base64 для их прямого встраивания." ")
    # -- Поля из бывшего AudioDefaults --
    format: str = Field(
        "wav",
        description="Желаемый формат аудиофайла. Примеры: «wav», «mp3», «flac», «aac». ")
    sample_rate_hz: int = Field(
        48000,
        description="Качество звука в герцах, влияющее на точность воспроизведения. Примеры: 48000, 44100, 96000, 192000." ")
    channels: int = Field(
        2,
        description="Количество аудиоканалов. Примеры: 2 (стерео), 1 (моно), 6 (5.1 surround), 8 (7.1 surround)." ")
    style: str = Field(
        None,
        description="Описывает музыкальный жанр, темп и элементы для этого трека. Примеры: «трэп-поп-рэп, 145 BPM, свинговые хэты, суб-бас», «оркестровая партитура с широкими струнными и драматической перкуссией, 60 BPM», «lo-fi хип-хоп, 80 BPM, джазовые аккорды, треск винила», «синтвейв с арпеджиированными басовыми линиями и ретро-барабанами, 120 BPM». ")


class Dialogue(BaseModel):
    """Определяет произносимые реплики и то, как они представлены."""

    character: str = Field(
        ...,
        description="Персонаж, который говорит. Примеры: «Никс Сайфер», «Таинственный незнакомец», «Голос системы ИИ», «Рассказчик». ")
    line: str = Field(
        ...,
        description="Точная реплика диалога или текста песни. Примеры: «Splash-cash, bling-blap—pool water pshh! Charts skrrt! like my wave, hot tropics whoosh!», «Воспоминания — это все, что осталось от того, чем мы когда-то были», «Доступ разрешен. Добро пожаловать в будущее», «В мире, где ничто не является тем, чем кажется...». ")
    subtitles: bool = Field(
        default=False,
        description="Логическое значение, определяющее, должны ли для этой строки отображаться субтитры. Субтитры всегда должны быть отключены. Никогда не добавляйте субтитры в видео." ")


class Performance(BaseModel):
    """Управляет анимированным исполнением персонажа в этом клипе."""

    mouth_shape_intensity: float = Field(
        None,
        description="Переопределение преувеличения синхронизации губ для конкретного клипа (0=незаметно, 1=преувеличено). Примеры: 0.85, 0.3, 1.0, 0.1." ")
    eye_contact_ratio: float = Field(
        None,
        description="Переопределение для конкретного клипа того, как часто персонаж смотрит в камеру. Примеры: 0.7, 0.1, 1.0, 0.5." ")


# -- Основная модель клипа --


class Clip(BaseModel):
    """Определяет один видеосегмент или кадр."""

    id: str = Field(
        ...,
        description="Уникальный идентификатор для этого конкретного клипа. Примеры: «S1_SplashCash», «Forest_Intro_001», «Cyberpunk_Market_Scene_3B», «Chase_Sequence_Final». ")
    shot: Shot
    subject: Subject
    scene: Scene
    visual_details: VisualDetails
    cinematography: Cinematography
    audio_track: AudioTrack
    dialogue: Dialogue
    performance: Performance
    duration_sec: int = Field(
        ...,
        description="Точная продолжительность этого клипа в секундах. Примеры: 8, 15, 3, 30, 45." ")
    aspect_ratio: str = Field(
        "16:9",
        description="Соотношение сторон для этого конкретного клипа. Примеры: «16:9» (стандартный широкоэкранный), «9:16» (вертикальный/мобильный), «2.35:1» (кинематографический), «4:3» (классический), «1:1» (квадратный)." ")


class CharacterProfile(BaseModel):
    """Подробный, последовательный профиль основных атрибутов персонажа."""

    name: str = Field(
        ...,
        description="Основное имя персонажа. Примеры: «Никс Сайфер», «Каэлен Тенемант», «Отряд 734», «Доктор Сара Чен». ")
    age: int = Field(
        ...,
        description="Видимый возраст персонажа. Примеры: 27, 350, 5, 72, 16." ")
    height: str = Field(
        ...,
        description="Рост персонажа, может включать несколько единиц измерения. Примеры: «5'8" / 173 см», «7'2" / 218 см», «4'11" / 150 см», «6'0" / 183 см». ")
    build: str = Field(
        ...,
        description="Описывает тип телосложения и телосложение персонажа. Примеры: «худощавый, спортивный, плечи пловца», «коренастый и мускулистый», «хрупкий и эфирный», «высокий и долговязый с грацией танцора», «компактный и мощный». ")
    skin_tone: str = Field(
        ...,
        description="Определяет цвет и текстуру кожи персонажа. Примеры: «темно-бронзовый с легким солнечным сиянием», «бледный фарфор с россыпью веснушек», «насыщенный эбеновый с естественным сиянием», «оливковый с обветренной текстурой», «металлические, переливающиеся чешуйки». ")
    hair: str = Field(
        ...,
        description="Описывает цвет, длину и стиль волос. Примеры: «иссиня-черные, до плеч, гладко зачесанные назад и мокрые», «серебристо-белая стрижка пикси с асимметричной челкой», «каштановые локоны, ниспадающие ниже плеч», «ежик платиновый блонд», «лысый с замысловатыми узорами хной». ")
    eyes: str = Field(
        ...,
        description="Подробно описывает форму и цвет глаз персонажа. Примеры: «миндалевидные карие с легкими золотыми вкраплениями», «широкие, льдисто-голубые и пронзительные», «темно-карие с теплыми янтарными бликами», «зеленые глаза с гетерохромией (один голубой)», «светящиеся малиновые без зрачков». ")
    distinguishing_marks: str = Field(
        None,
        description="Уникальные особенности, такие как татуировки, шрамы или пирсинг. Примеры: «крошечная татуировка в виде звезды за правым ухом; золотой гвоздик в верхней левой спирали», «рваный шрам в виде молнии на левом виске», «замысловатая татуировка на рукаве, изображающая океанские волны», «сеть светящихся кибернетических имплантатов вдоль линии челюсти». ")
    demeanour: str = Field(
        ...,
        description="Типичная личность, настроение и выражение лица персонажа. Примеры: «игриво самоуверенный, почти вызывающая ухмылка», «стоический и уставший от мира с добрыми глазами», «маниакальная энергия с непредсказуемыми перепадами настроения», «спокойный и собранный со скрытой интенсивностью», «теплый и доступный с заразительным смехом». ")
    # -- Поля из бывшего GlobalStyle --
    default_outfit: str = Field(
        ...,
        description="Стандартный или основной наряд персонажа. Примеры: «бикини цвета металлического коралла, зеркальные солнцезащитные очки, золотые серьги-кольца», «угольно-серое пальто поверх винтажной футболки с группой и потертых джинсов», «струящееся белое льняное платье с тонкой вышивкой», «тактический черный комбинезон с разгрузочным жилетом», «костюм-тройка в тонкую полоску с карманными часами». ")
    mouth_shape_intensity: float = Field(
        ...,
        description="Управляет преувеличением движений рта для синхронизации губ (0=незаметно, 1=преувеличено). Примеры: 0.85, 0.5, 1.0, 0.25." ")
    eye_contact_ratio: float = Field(
        ...,
        description="Процент времени, в течение которого персонаж должен смотреть прямо в камеру. Примеры: 0.7, 0.2, 0.9, 0.5." ")


class VideoSchema(BaseModel):
    """Корневая модель, содержащая список персонажей для создания."""

    characters: List[CharacterProfile] = Field(
        ...,
        description="Подробный, последовательный профиль основных атрибутов персонажа." ")
    clips: List[Clip] = Field(
        ...,
        description="Массив, содержащий определения для каждого отдельного видеосегмента или кадра." ")


client = genai.Client()


def generate_scenes(
    idea: str,
    output_dir: str,
    number_of_scenes: int,
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
    logger.info(f"Создание {number_of_scenes} сцен для идеи: '{idea}'")

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=f"""
        {idea}
        Видео должно состоять максимум из {number_of_scenes} сцен, каждая продолжительностью 8 секунд.
        """,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=VideoSchema.model_json_schema(),
        ),
    )

    video_schema = json.loads(response.text)

    with open(os.path.join(output_dir, "script.json"), "w") as f:
        f.write(response.text)

    return video_schema


def generate_video(
    prompt: str,
    image: Image,
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
    # Создайте выходной каталог, если он не существует
    os.makedirs(output_dir, exist_ok=True)

    # Создать видео
    logger.info(f"Создание видео в {aspect_ratio} из подсказки: {prompt[:100]}...")
    operation = client.models.generate_videos(
        model="veo-3.0-generate-preview",
        prompt=prompt,
        image=image,
        config=genai.types.GenerateVideosConfig(
            aspect_ratio="16:9",  # в настоящее время поддерживается только 16:9
            # person_generation="allow_all",
        ),
    )
    # Дождитесь создания видео
    while not operation.done:
        logger.info("Ожидание создания видео...")
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.response.generated_videos is None:
        raise RuntimeError(operation.response)

    for video in operation.response.generated_videos:
        client.files.download(file=video.video)
        video.video.save(os.path.join(output_dir, fname))

    return os.path.join(output_dir, fname)


def generate_image(
    prompt: str,
    output_dir: str = "images",
    fname: str = "image.png",
) -> Image:
    """Создает изображение из текстовой подсказки."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Создание изображения с подсказкой: {prompt[:100]}...")

    image = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=genai.types.GenerateImagesConfig(
            aspect_ratio="16:9",
        ),
    )

    image.generated_images[0].image.save(os.path.join(output_dir, fname))

    return image.generated_images[0].image


def edit_image(
    image: Image,
    prompt: str,
    output_dir: str = "images",
    fname: str = "edited_image.png",
) -> types.Image:
    """Редактирует изображение с помощью текстовой подсказки."""

    prompt = f"Отредактируйте изображение, чтобы оно соответствовало следующей подсказке: {prompt}"
    logger.info(f"Редактирование изображения с подсказкой: {prompt[:100]}...")

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=[
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": image.mime_type,
                            "data": image.image_bytes,
                        }
                    },
                ],
            }
        ],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            logger.info(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            image.save(os.path.join(output_dir, fname))

    return types.Image.from_file(location=os.path.join(output_dir, fname))


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
    logger.info(f"Объединение {len(video_files)} видеофайлов в {output_file}")
    # Загрузить каждый видеоклип
    clips = [VideoFileClip(file) for file in video_files]

    # Объединить видеоклипы
    final_clip = concatenate_videoclips(clips)

    # Записать окончательный видеофайл
    output_path = os.path.join(output_dir, output_file)
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
    )

    return os.path.join(output_dir, output_file)


def generate_vlog(
    idea: str,
    number_of_scenes: int = 4,
    aspect_ratio: str = "16:9",
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
    # Создайте уникальный подкаталог для этого влога
    vlog_subdir_name = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")[:35]
    vlog_output_dir = os.path.join(output_dir, vlog_subdir_name)
    os.makedirs(vlog_output_dir, exist_ok=True)
    logger.info(f"Начало создания влога для идеи: '{idea}'")
    logger.info(f"Вывод будет сохранен в '{vlog_output_dir}'")

    script = generate_scenes(
        idea=idea,
        output_dir=vlog_output_dir,
        number_of_scenes=number_of_scenes,
    )

    video_files = []

    logger.info("Создание начального изображения...")
    start_image = generate_image(
        prompt=json.dumps(
            {"characters": script["characters"], "clips": [script["clips"][0]]}
        ),
        output_dir=vlog_output_dir,
        fname="start_image.png",
    )

    for n, scene in enumerate(script["clips"]):
        logger.info(f"Обработка сцены {n + 1}/{len(script['clips'])}")
        scene_object = {"characters": script["characters"], "clips": [scene]}

        if n > 0:
            logger.info(f"Редактирование изображения для сцены {n + 1}")
            scene_image = edit_image(
                image=start_image,
                prompt=json.dumps(scene_object),
                output_dir=vlog_output_dir,
                fname=f"scene_{n}_image.png",
            )
        else:
            scene_image = start_image

        logger.info(f"Создание видео для сцены {n + 1}")
        video_file = generate_video(
            json.dumps(scene_object),
            scene_image,
            fname=f"video_{n}.mp4",
            output_dir=vlog_output_dir,
            aspect_ratio=aspect_ratio,
        )
        video_files.append(video_file)
    merge_videos(video_files, "vlog.mp4", output_dir=vlog_output_dir)


if __name__ == "__main__":
    ideas = [
        ("Реалистичная реклама энергетического напитка для спортсменов.", 3),
        (
            "Штурмовик, будучи растерянным туристом в центре Лондона, жалуется на погоду.",
            4,
        ),
        ("Мультфильм для детей о том, как работает сложение", 3),
    ]

    for idea, number_of_scenes in ideas:
        try:
            generate_vlog(
                idea=idea,
                number_of_scenes=number_of_scenes,
            )
        except Exception as e:
            print("Повторный запуск...")
            generate_vlog(
                idea=idea,
                number_of_scenes=number_of_scenes,
            )
