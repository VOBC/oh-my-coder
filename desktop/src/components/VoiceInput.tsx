'use strict';

import React, { useState, useRef, useCallback, useEffect } from 'react';

// ---------------------------------------------------------------------------
// VoiceInput Component
// Captures raw PCM audio via AudioContext + ScriptProcessorNode,
// encodes to WAV, sends to main process for Whisper transcription.
// ---------------------------------------------------------------------------

interface VoiceInputProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

export const VoiceInput = ({
  onResult,
  disabled = false,
}: VoiceInputProps) => {
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const pcmChunksRef = useRef<Float32Array[]>([]);

  const isSupported =
    typeof window !== 'undefined' &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === 'function';

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  // Auto-clear error after 3 seconds.
  useEffect(() => {
    if (!errorMsg) return;
    const t = setTimeout(() => setErrorMsg(''), 3000);
    return () => clearTimeout(t);
  }, [errorMsg]);

  const cleanup = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
  };

  // Encode Float32Array PCM samples to WAV bytes
  const encodeWAV = (samples: Float32Array, sampleRate: number): Uint8Array => {
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const dataSize = samples.length * (bitsPerSample / 8);
    const bufferSize = 44 + dataSize;

    const buffer = new ArrayBuffer(bufferSize);
    const view = new DataView(buffer);

    // RIFF header
    writeStr(view, 0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeStr(view, 8, 'WAVE');
    // fmt chunk
    writeStr(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    // data chunk
    writeStr(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }

    return new Uint8Array(buffer);
  };

  const writeStr = (view: DataView, offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  const toggleListening = useCallback(() => {
    if (!isSupported) {
      setErrorMsg('当前环境不支持录音');
      return;
    }

    if (isListening) {
      // Stop recording
      cleanup();
      setIsListening(false);

      // Merge PCM chunks and transcribe
      if (pcmChunksRef.current.length === 0) return;

      const totalLength = pcmChunksRef.current.reduce((sum, c) => sum + c.length, 0);
      const merged = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of pcmChunksRef.current) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }
      pcmChunksRef.current = [];

      const wavBytes = encodeWAV(merged, 16000);

      setIsTranscribing(true);
      setInterimText('识别中...');

      window.omc.whisper.transcribe(Array.from(wavBytes))
        .then((result: { ok: boolean; text: string; error?: string }) => {
          if (result.ok && result.text) {
            onResult(result.text);
          } else {
            setErrorMsg(result.error || '语音识别失败');
          }
        })
        .catch((err: unknown) => {
          console.error('[VoiceInput] Transcribe error:', err);
          setErrorMsg('语音识别失败，请重试');
        })
        .finally(() => {
          setIsTranscribing(false);
          setInterimText('');
        });

      return;
    }

    // Start recording
    pcmChunksRef.current = [];

    navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } })
      .then((stream) => {
        streamRef.current = stream;

        const audioCtx = new AudioContext({ sampleRate: 16000 });
        audioCtxRef.current = audioCtx;

        const source = audioCtx.createMediaStreamSource(stream);
        sourceRef.current = source;

        // ScriptProcessorNode to capture raw PCM
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          const channelData = e.inputBuffer.getChannelData(0);
          pcmChunksRef.current.push(new Float32Array(channelData));
        };

        source.connect(processor);
        processor.connect(audioCtx.destination);

        setIsListening(true);
        setInterimText('');
        setErrorMsg('');
      })
      .catch((err: unknown) => {
        console.error('[VoiceInput] getUserMedia error:', err);
        if (err instanceof Error && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')) {
          setErrorMsg('请在系统设置中允许麦克风权限');
        } else {
          setErrorMsg('无法访问麦克风');
        }
      });
  }, [isListening, isSupported, onResult]);

  const btnTitle = isListening
    ? '点击停止'
    : isTranscribing
    ? '识别中...'
    : '语音输入';

  return (
    <div className="voice-input">
      <button
        className={`voice-input__btn ${isListening ? 'voice-input__btn--active' : ''} ${isTranscribing ? 'voice-input__btn--transcribing' : ''}`}
        onClick={toggleListening}
        disabled={disabled}
        title={btnTitle}
        type="button"
      >
        {isListening ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2"/>
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        )}
      </button>

      {(isListening || isTranscribing) && (
        <div className="voice-input__indicator">
          <span className="voice-input__dot" />
          {interimText && <span className="voice-input__interim">{interimText}</span>}
        </div>
      )}

      {errorMsg && (
        <div className="voice-input__error">{errorMsg}</div>
      )}
    </div>
  );
};
