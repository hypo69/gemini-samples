// This example is using the Gemini 2.0 Flash experimental native image output
// npm install @google/genai
// GEMINI_API_KEY=your-api-key-here npm run start

const fs = require('fs');
const { GoogleGenAI } = require('@google/genai');

// Initialize the Google Gen AI client with your API key
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'your-api-key-here';
const ai = new GoogleGenAI({ apiKey: GEMINI_API_KEY });

// Define the model ID for Gemini 2.0 Flash experimental
const MODEL_ID = 'gemini-2.0-flash-exp';

// Helper function to save an image from binary data
function saveImage(data, filename) {
  fs.writeFileSync(filename, Buffer.from(data, 'base64'));
  console.log(`Image saved as ${filename}`);
}

async function generateImage(prompt, inputImagePath = null, outputImagePath) {
  console.log(`Generating image with prompt: "${prompt}"${inputImagePath ? ' and input image' : ''}...`);
  
  // Define generation config to include image output
  const config = {
    responseModalities: ['Text', 'Image']
  };

  // Prepare the contents array for the API call
  const contents = [];
  
  // Add the prompt text
  contents.push(prompt);
  
  // Add the input image if provided
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
    // Generate the image
    const response = await ai.models.generateContent({
      model: MODEL_ID,
      contents,
      config
    });

    let textResponse = null;

    // Process the response
    for (const part of response.candidates[0].content.parts) {
      if (part.inlineData) {
        // Save the image
        saveImage(part.inlineData.data, outputImagePath);
      } else if (part.text) {
        // Store the text
        textResponse = part.text;
        console.log('\nDescription:');
        console.log(part.text);
      }
    }

    return textResponse;
  } catch (error) {
    console.error('Error generating image:', error);
    return null;
  }
}

async function runDemo() {
  // Example 1: Generate a car image from text prompt only
  await generateImage(
    "An Image of a black sports car in the style of a 1960s Ferrari and create a 1 sentence marketing description",
    null,
    'car.png'
  );

  // Example 2: Modify the generated image to make the car red
  await generateImage(
    "Make the car red",
    'car.png',
    'car_red.png'
  );
}

// Run the demo
runDemo(); 