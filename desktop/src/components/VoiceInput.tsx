'use strict';

import React, { useState, useRef, useCallback, useEffect } from 'react';

// ---------------------------------------------------------------------------
// VoiceInput Component
// Uses Electron IPC for Whisper speech recognition via @napi-rs/whisper in main process.
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

  const isSupported =
    typeof window !== 'undefined' &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === 'function';

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

  // Convert audio Blob to PCM Float32Array (16kHz mono) for Whisper
  const blobToPCM = async (blob: Blob): Promise<Float32Array> => {
    const arrayBuffer = await blob.arrayBuffer();
    const audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    return new Float32Array(audioBuffer.getChannelData(0));
  };

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
            // Decode to PCM and send to main process for Whisper transcription
            const pcmData = await blobToPCM(blob);
            const result = await window.omc.whisper.transcribe(Array.from(pcmData));
            
            if (result.ok && result.text) {
              onResult(result.text);
            } else {
              setErrorMsg(result.error || '语音识别失败');
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

  // Compute button status label (simplified, no pre-loading needed)
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