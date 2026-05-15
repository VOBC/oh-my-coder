'use strict';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { loadWhisper, transcribeAudio } from '../whisper-loader.js';

// ---------------------------------------------------------------------------
// VoiceInput Component
// Uses whisper-loader.js for WASM-based speech recognition.
// Works in: Electron renderer, Chrome, Safari, Firefox — Windows + Mac + Linux.
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

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const whisperLoadedRef = useRef(false);
  const whisperLoadErrorRef = useRef<string | null>(null);

  const isSupported =
    typeof window !== 'undefined' &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === 'function';

  // Pre-load whisper model once on mount so first recording is instant.
  useEffect(() => {
    loadWhisper()
      .then(() => { whisperLoadedRef.current = true; })
      .catch((err: unknown) => {
        console.warn('[VoiceInput] Whisper WASM load failed:', err);
        whisperLoadErrorRef.current = err instanceof Error ? err.message : String(err);
      });
  }, []);

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // Auto-clear error after 3 seconds.
  useEffect(() => {
    if (!errorMsg) return;
    const t = setTimeout(() => setErrorMsg(''), 3000);
    return () => clearTimeout(t);
  }, [errorMsg]);

  const toggleListening = useCallback(() => {
    if (!isSupported) {
      setErrorMsg('当前环境不支持录音');
      return;
    }

    if (isListening) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    chunksRef.current = [];

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.onstart = () => {
          setIsListening(true);
          setInterimText('');
          setErrorMsg('');
        };

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        mediaRecorder.onstop = async () => {
          setIsListening(false);

          // Release microphone.
          stream.getTracks().forEach((t) => t.stop());

          if (chunksRef.current.length === 0) return;

          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });

          setIsTranscribing(true);
          setInterimText('识别中...');

          try {
            const text = await transcribeAudio(blob);
            if (text) {
              onResult(text);
            } else {
              setErrorMsg('未能识别到语音内容');
            }
          } catch (err: unknown) {
            console.error('[VoiceInput] Transcribe error:', err);
            setErrorMsg('语音识别失败，请重试');
          } finally {
            setIsTranscribing(false);
            setInterimText('');
          }
        };

        mediaRecorder.onerror = () => {
          setIsListening(false);
          setInterimText('');
          setErrorMsg('录音出错');
        };

        // Record in 1-second chunks so we can stop quickly on button press.
        mediaRecorder.start(1000);
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

  // Compute button status label.
  const btnTitle = isListening
    ? '点击停止'
    : isTranscribing
    ? '识别中...'
    : whisperLoadErrorRef.current
    ? '语音模型加载失败'
    : whisperLoadedRef.current
    ? '语音输入'
    : '加载语音模型...';

  return (
    <div className="voice-input">
      <button
        className={`voice-input__btn ${isListening ? 'voice-input__btn--active' : ''} ${isTranscribing ? 'voice-input__btn--transcribing' : ''}`}
        onClick={toggleListening}
        disabled={disabled || !!whisperLoadErrorRef.current}
        title={btnTitle}
        type="button"
      >
        {isListening ? (
          // Stop icon (filled square)
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2"/>
          </svg>
        ) : (
          // Microphone icon
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

// No module.exports needed — already exported via `export const VoiceInput` above