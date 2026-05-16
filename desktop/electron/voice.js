'use strict';

// electron/voice.js — Whisper speech recognition via @napi-rs/whisper
const path = require('path');
const { readFile } = require('node:fs/promises');

let whisper = null;

async function getWhisper() {
  if (whisper) return whisper;
  
  const { Whisper } = await import('@napi-rs/whisper');
  
  const modelPath = path.join(process.env.APPDATA || process.env.HOME, '.omc', 'whisper', 'ggml-base.bin');
  const modelBuf = await readFile(modelPath);
  
  whisper = new Whisper(modelBuf);
  return whisper;
}

// Transcribe raw audio bytes (WAV or PCM) to text
async function transcribeAudio(audioBytes) {
  const { WhisperFullParams, WhisperSamplingStrategy } = await import('@napi-rs/whisper');
  const w = await getWhisper();
  
  // audioBytes is a number array from IPC (Uint8Array from frontend)
  const buf = Buffer.from(audioBytes);
  
  // Try decodeAudioAsync first (handles WAV, MP3, etc.)
  let pcm;
  try {
    pcm = await w.decodeAudioAsync(buf, 'audio.wav');
  } catch {
    // If decode fails, treat as raw PCM Float32Array bytes
    // Each float32 = 4 bytes
    pcm = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  }
  
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
