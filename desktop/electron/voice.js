'use strict';

// electron/voice.js — Whisper speech recognition via @napi-rs/whisper
const path = require('path');
const { readFile } = require('node:fs/promises');

// Lazy-loaded whisper instance
let whisper = null;

async function getWhisper() {
  if (whisper) return whisper;
  
  const { Whisper } = await import('@napi-rs/whisper');
  
  // Load GGML base model
  const modelPath = path.join(process.env.APPDATA || process.env.HOME, '.omc', 'whisper', 'ggml-base.bin');
  const modelBuf = await readFile(modelPath);
  
  whisper = new Whisper(modelBuf);
  return whisper;
}

// Transcribe raw audio bytes to text
async function transcribeAudio(audioBytes) {
  const { WhisperFullParams, WhisperSamplingStrategy, decodeAudioAsync } = await import('@napi-rs/whisper');
  const w = await getWhisper();
  
  // audioBytes is a number array from IPC — convert back to Buffer/Uint8Array
  const audioBuf = Uint8Array.from(audioBytes);
  
  // Decode audio to PCM Float32Array (16kHz mono)
  const pcm = await decodeAudioAsync(audioBuf, 'input.webm');
  
  // Build params for Chinese transcription
  const params = new WhisperFullParams(WhisperSamplingStrategy.Greedy);
  params.language = 'zh';
  params.printProgress = false;
  params.printRealtime = false;
  params.printTimestamps = false;
  
  // Run full transcription — returns a string
  const result = w.full(params, pcm);
  
  return result || '';
}

module.exports = {
  getWhisper,
  transcribeAudio,
};
