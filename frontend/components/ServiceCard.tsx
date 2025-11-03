import { useState } from 'react'
import { ToastType } from './Toast'

interface Props {
  serviceName: string
  title: string
  description: string
  placeholder: string
  icon: React.ReactNode
  verified: boolean
  disabled?: boolean
  defaultValue?: string
  onVerify: (success: boolean) => void
}

export default function ServiceCard({
  serviceName,
  title,
  description,
  placeholder,
  icon,
  verified,
  disabled = false,
  defaultValue = '',
  onVerify
}: Props) {
  const [apiKey, setApiKey] = useState(defaultValue)
  const [loading, setLoading] = useState(false)
  const [showKey, setShowKey] = useState(false)

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

  const handleVerify = async () => {
    if (!apiKey.trim() || loading || disabled) return

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/verify/${serviceName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
      })

      if (response.ok) {
        onVerify(true)
      } else {
        onVerify(false)
      }
    } catch (error) {
      console.error('Verification failed:', error)
      onVerify(false)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setApiKey('')
    onVerify(false)
  }

  return (
    <div className="card hover:shadow-lg transition-shadow duration-300">
      {/* 카드 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`text-${serviceName === 'slack' ? 'purple' : serviceName === 'telegram' ? 'blue' : 'gray'}-500`}>
            {icon}
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-800">{title}</h3>
            <p className="text-sm text-gray-600">{description}</p>
          </div>
        </div>
        {verified && (
          <span className="bg-green-100 text-green-800 text-xs font-semibold px-3 py-1 rounded-full">
            검증됨
          </span>
        )}
      </div>

      {/* 입력 필드 */}
      <div className="space-y-3">
        <div className="relative">
          <input
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            className="input-field pr-20"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 text-sm"
          >
            {showKey ? '숨기기' : '보기'}
          </button>
        </div>

        {/* 버튼들 */}
        <div className="flex space-x-2">
          <button
            onClick={handleVerify}
            disabled={disabled || loading || !apiKey.trim()}
            className={`flex-1 font-bold py-2 px-4 rounded-lg transition-colors duration-200 ${
              verified
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'btn-primary'
            } disabled:bg-gray-300 disabled:cursor-not-allowed`}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                검증 중...
              </span>
            ) : verified ? (
              <>
                <span className="mr-1">✓</span> 검증됨
              </>
            ) : disabled ? (
              '서비스 준비 중'
            ) : (
              '키 검증'
            )}
          </button>

          {verified && (
            <button
              onClick={handleReset}
              disabled={loading}
              className="btn-danger"
            >
              초기화
            </button>
          )}
        </div>

        {/* 상태 메시지 */}
        {disabled && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-yellow-800 text-sm flex items-center">
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              이 서비스는 현재 개발 중입니다. 곧 사용할 수 있습니다!
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
