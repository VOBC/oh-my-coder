import React, { useState, useRef, useCallback, useEffect } from 'react';

interface VoiceInputProps {
  onResult: (text: string) => void;
  disabled?: boolean;
  lang?: string;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ 
  onResult, 
  disabled = false,
  lang = 'zh-CN'
}) => {
  const [isListening, setIsListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const recognitionRef = useRef<any>(null);
  const isSupported = typeof window !== 'undefined' && 
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  // Check if actually available (Electron may have the API but not the service)
  const [actuallyAvailable, setActuallyAvailable] = useState(isSupported);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  // Clear error after 4s
  useEffect(() => {
    if (!errorMsg) return;
    const t = setTimeout(() => setErrorMsg(''), 4000);
    return () => clearTimeout(t);
  }, [errorMsg]);

  const toggleListening = useCallback(() => {
    if (!isSupported || !actuallyAvailable) {
      setErrorMsg('语音输入仅支持浏览器版本，桌面端暂不可用');
      return;
    }

    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      setInterimText('');
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || 
                              (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = lang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setInterimText('');
      setErrorMsg('');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      setInterimText(interim);

      if (final) {
        onResult(final);
        setInterimText('');
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('[VoiceInput] Error:', event.error);
      setIsListening(false);
      setInterimText('');
      
      if (event.error === 'not-allowed') {
        setErrorMsg('请在系统设置中允许麦克风权限');
      } else if (event.error === 'network' || event.error === 'service-not-available') {
        setActuallyAvailable(false);
        setErrorMsg('语音输入仅支持浏览器版本，桌面端暂不可用');
      } else if (event.error === 'no-speech') {
        // Silent - user just didn't speak
      } else if (event.error !== 'aborted') {
        setErrorMsg(`语音识别出错: ${event.error}`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimText('');
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [isListening, isSupported, actuallyAvailable, lang, onResult]);

  return (
    <div className="voice-input" title={isListening ? '点击停止' : (actuallyAvailable ? '语音输入' : '语音输入仅支持浏览器版本')}>
      <button
        className={`voice-input__btn ${isListening ? 'voice-input__btn--active' : ''} ${!actuallyAvailable ? 'voice-input__btn--disabled' : ''}`}
        onClick={toggleListening}
        disabled={disabled}
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
      {isListening && (
        <div className="voice-input__indicator">
          <span className="voice-input__dot"></span>
          {interimText && <span className="voice-input__interim">{interimText}</span>}
        </div>
      )}
      {errorMsg && (
        <div className="voice-input__error">{errorMsg}</div>
      )}
    </div>
  );
};
