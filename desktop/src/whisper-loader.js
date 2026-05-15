// whisper-loader.js — ES Module for Whisper.cpp WASM

let whisperInstance = null;
let modelBuffer = null;
let isLoading = false;
let loadPromise = null;

// Load WASM module
async function loadWhisper() {
  if (whisperInstance) return whisperInstance;
  if (loadPromise) return loadPromise;

  isLoading = true;
  loadPromise = (async () => {
    try {
      // In Electron renderer, use fetch to load WASM
      // WASM files are in /whisper/ (relative to desktop/public/whisper/)
      const wasmUrl = '/whisper/whisper.wasm';
      const jsUrl = '/whisper/whisper.js';

      // Load whisper.js (creates global `whisper` function)
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = jsUrl;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });

      // whisper.js creates global `whisper` function
      // Call it to initialize WASM module
      whisperInstance = await window.whisper({
        wasmUrl: wasmUrl,
      });

      isLoading = false;
      return whisperInstance;
    } catch (err) {
      isLoading = false;
      loadPromise = null;
      throw err;
    }
  })();

  return loadPromise;
}

// Load model file
async function loadModel() {
  if (modelBuffer) return modelBuffer;

  const modelUrl = '/whisper/ggml-base.bin';
  const response = await fetch(modelUrl);
  if (!response.ok) throw new Error(`Failed to load model: ${response.statusText}`);
  modelBuffer = await response.arrayBuffer();
  return modelBuffer;
}

// Convert Blob to AudioBuffer (16kHz mono 16-bit PCM)
async function decodeAudio(audioBlob) {
  const arrayBuffer = await audioBlob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)({
    sampleRate: 16000,
  });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  
  // Convert to mono 16-bit PCM
  const channelData = audioBuffer.getChannelData(0); // mono
  const pcmBuffer = new Int16Array(channelData.length);
  for (let i = 0; i < channelData.length; i++) {
    const s = Math.max(-1, Math.min(1, channelData[i]));
    pcmBuffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  
  return pcmBuffer.buffer;
}

// Main API: transcribe audio blob to text
async function transcribeAudio(audioBlob) {
  const whisper = await loadWhisper();
  const modelData = await loadModel();
  const pcmData = await decodeAudio(audioBlob);

  // Call Whisper WASM to transcribe
  const result = whisper.transcribe(modelData, pcmData, {
    language: 'zh',
    translate: false,
  });

  return result.text || '';
}

export {
  loadWhisper,
  transcribeAudio,
  loadModel,
};
