import { useEffect } from 'react'
import { useRouter } from 'next/router'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // 바로 대시보드로 리다이렉트
    router.replace('/dashboard')
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">125 Build Automation</h1>
        <p>대시보드로 이동 중입니다...</p>
      </div>
    </div>
  )
}
