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

// Transcribe PCM Float32Array (16kHz mono) to text
async function transcribeAudio(pcmData) {
  const { WhisperFullParams, WhisperSamplingStrategy } = await import('@napi-rs/whisper');
  const w = await getWhisper();
  
  // pcmData is a number array from IPC — convert to Float32Array
  const pcm = Float32Array.from(pcmData);
  
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
