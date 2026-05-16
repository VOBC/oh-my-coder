'use strict';

// electron/voice.js — Whisper speech recognition via @napi-rs/whisper
const path = require('path');
const { readFile } = require('node:fs/promises');
const { Converter } = require('opencc-js');

// Traditional to Simplified Chinese converter
const tradToSimp = new Converter('taiwan', 'china');

let whisper = null;

async function getWhisper() {
  if (whisper) return whisper;

  const { Whisper } = await import('@napi-rs/whisper');

  const modelPath = path.join(
    process.env.APPDATA || process.env.HOME,
    '.omc',
    'whisper',
    'ggml-base.bin'
  );
  const modelBuf = await readFile(modelPath);

  whisper = new Whisper(modelBuf);
  console.log('[voice] Whisper model loaded');
  return whisper;
}

// Transcribe WAV audio bytes to text
async function transcribeAudio(audioBytes) {
  const { WhisperFullParams, WhisperSamplingStrategy } = await import('@napi-rs/whisper');
  const w = await getWhisper();
  const { decodeAudioAsync } = await import('@napi-rs/whisper');

  // audioBytes comes as a number array from IPC (Array.from(Uint8Array))
  const buf = Buffer.from(audioBytes);
  console.log('[voice] Received', buf.length, 'bytes');

  // Decode WAV → PCM Float32Array (module-level function, not instance method)
  let pcm;
  try {
    pcm = await decodeAudioAsync(buf, 'audio.wav');
    console.log('[voice] Decoded PCM, samples:', pcm.length);
  } catch (decodeErr) {
    console.error('[voice] decodeAudioAsync failed:', decodeErr.message);
    throw new Error('音频解码失败: ' + decodeErr.message);
  }

  if (pcm.length < 100) {
    console.log('[voice] Audio too short, skipping');
    return '';
  }

  // Build params for Chinese transcription
  const params = new WhisperFullParams(WhisperSamplingStrategy.Greedy);
  params.language = 'zh';
  params.printProgress = false;
  params.printRealtime = false;
  params.printTimestamps = false;

  // Run full transcription — returns a string
  console.log('[voice] Running transcription...');
  const raw = w.full(params, pcm);
  console.log('[voice] Raw result:', JSON.stringify(raw));

  // Convert Traditional Chinese to Simplified Chinese
  const result = raw ? tradToSimp(raw) : '';
  console.log('[voice] Simplified result:', JSON.stringify(result));

  return result;
}

module.exports = {
  getWhisper,
  transcribeAudio,
};
