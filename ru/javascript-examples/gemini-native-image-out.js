// Этот пример использует экспериментальный нативный вывод изображений Gemini 2.0 Flash
// npm install @google/genai
// GEMINI_API_KEY=ваш-api-ключ-здесь npm run start

const fs = require('fs');
const { GoogleGenAI } = require('@google/genai');

// Инициализируйте клиент Google Gen AI вашим ключом API
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'ваш-api-ключ-здесь';
const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

// Определите идентификатор модели для Gemini 2.0 Flash experimental
const MODEL_ID = 'gemini-2.0-flash-exp';

// Вспомогательная функция для сохранения изображения из двоичных данных
function saveImage(data, filename) {
  fs.writeFileSync(filename, Buffer.from(data, 'base64'));
  console.log(`Изображение сохранено как ${filename}`);
}

async function generateImage(prompt, inputImagePath = null, outputImagePath) {
  console.log(`Создание изображения с подсказкой: "${prompt}"${inputImagePath ? ' и входным изображением' : ''}...`);
  
  // Определите конфигурацию генерации, чтобы включить вывод изображения
  const config = {
    responseModalities: ['Text', 'Image']
  };

  // Подготовьте массив содержимого для вызова API
  const contents = [];
  
  // Добавьте текст подсказки
  contents.push(prompt);
  
  // Добавьте входное изображение, если оно предоставлено
  if (inputImagePath) {
    const imageData = fs.readFileSync(inputImagePath);
    contents.push({
      inlineData: {
        data: imageData.toString('base64'),
        mimeType: 'image/png'
      }
    });
  }

  try {
    // Сгенерировать изображение
    const response = await ai.models.generateContent({
      model: MODEL_ID,
      contents,
      config
    });

    let textResponse = null;

    // Обработать ответ
    for (const part of response.candidates[0].content.parts) {
      if (part.inlineData) {
        // Сохранить изображение
        saveImage(part.inlineData.data, outputImagePath);
      } else if (part.text) {
        // Сохранить текст
        textResponse = part.text;
        console.log('\nОписание:');
        console.log(part.text);
      }
    }

    return textResponse;
  } catch (error) {
    console.error('Ошибка при создании изображения:', error);
    return null;
  }
}

async function runDemo() {
  // Пример 1: Создание изображения автомобиля только из текстовой подсказки
  await generateImage(
    "Изображение черного спортивного автомобиля в стиле Ferrari 1960-х годов и создайте маркетинговое описание из 1 предложения",
    null,
    'car.png'
  );

  // Пример 2: Измените сгенерированное изображение, чтобы сделать автомобиль красным
  await generateImage(
    "Сделайте машину красной",
    'car.png',
    'car_red.png'
  );
}

// Запустить демонстрацию
runDemo();
