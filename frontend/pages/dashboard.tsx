import { useState, useEffect } from 'react'
import ServiceCard from '../components/ServiceCard'
import Toast, { ToastType } from '../components/Toast'

export default function Dashboard() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

  const [verifiedServices, setVerifiedServices] = useState<Record<string, boolean>>({})
  const [toast, setToast] = useState<{message: string, type: ToastType} | null>(null)

  // 기본 API 키들 (환경변수나 하드코딩된 값)
  const defaultApiKeys = {
    telegram: '8288922587:AAHUADrjbeLFSTxS_Hx6jEDEbAW88dOzgNY', // @mgs_hub_bot
    slack: 'xoxp-9101858700288-9101858708496-9811755934066-f1e8d3fff60be56ed45d44f0e88dbda3'
  }

  // 컴포넌트 마운트 시 - 자동 검증 제거 (테스트 모드)
  useEffect(() => {
    // 테스트를 위해 기본적으로 검증된 상태로 설정
    setVerifiedServices({
      telegram: true,
      slack: true
    })
  }, [])

  // 토스트 표시
  const showToast = (message: string, type: ToastType) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  // 검증 성공 콜백
  const handleVerify = (serviceName: string, success: boolean) => {
    setVerifiedServices(prev => ({
      ...prev,
      [serviceName]: success
    }))

    if (success) {
      showToast(`${serviceName} API 키가 성공적으로 검증되었습니다! ✅`, 'success')
    } else {
      showToast(`${serviceName} API 키 검증에 실패했습니다 ❌`, 'error')
    }
  }

  const services = [
    {
      name: 'telegram',
      title: 'Telegram',
      description: 'Telegram Bot Token',
      placeholder: '123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
      icon: (
        <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
        </svg>
      )
    },
    {
      name: 'slack',
      title: 'Slack',
      description: 'Slack Bot Token',
      placeholder: 'xoxb-your-bot-token-here',
      icon: (
        <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
          <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
        </svg>
      )
    }
  ]

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 토스트 알림 */}
      {toast && (
        <Toast message={toast.message} type={toast.type} />
      )}

      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                API 키 검증 대시보드
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                단순 검증 버전 (로그인 없음)
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 요약 카드 */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-6 mb-8 text-white">
          <h2 className="text-xl font-bold mb-2">🎯 검증 현황</h2>
          <p className="mb-4">
            총 {services.length}개 서비스 중{' '}
            {Object.values(verifiedServices).filter(Boolean).length}개 검증 완료
          </p>
          <div className="flex space-x-2">
            {Object.entries(verifiedServices).map(([service, verified]) => (
              <span
                key={service}
                className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  verified ? 'bg-green-400 text-green-900' : 'bg-gray-300 text-gray-700'
                }`}
              >
                {service}: {verified ? '✓' : '✗'}
              </span>
            ))}
          </div>
        </div>

        {/* 서비스 카드 그리드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
          {services.map((service) => (
            <ServiceCard
              key={service.name}
              serviceName={service.name}
              title={service.title}
              description={service.description}
              placeholder={service.placeholder}
              icon={service.icon}
              verified={verifiedServices[service.name] || false}
              defaultValue={defaultApiKeys[service.name as keyof typeof defaultApiKeys] || ''}
              onVerify={(success) => handleVerify(service.name, success)}
            />
          ))}
        </div>

        {/* 도움말 */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-blue-900 mb-2">
            📚 API 키 발급 가이드
          </h3>
          <ul className="space-y-2 text-blue-800 text-sm">
            <li>
              <strong>Telegram:</strong> @BotFather에게 "/newbot" 메시지를 보내 새 봇을 생성하세요.
            </li>
            <li>
              <strong>Slack:</strong> Slack API (api.slack.com)에서 앱을 생성하고 Bot Token을 발급받으세요.
            </li>
          </ul>
        </div>
      </main>
    </div>
  )
}
