// 📁 layouts/MobileLayout.tsx
// 목표: 80줄 이하

import { useState } from 'react';
import ChatContainer from '@/components/chat/ChatContainer';
import HamburgerMenu from '@/components/mobile/HamburgerMenu';
import DashboardPanel from '@/components/dashboard/DashboardPanel';

export default function MobileLayout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="h-screen relative">
      {/* 헤더 */}
      <header className="bg-yellow-400 p-4 flex justify-between">
        <h1 className="font-bold">🍋 limone.dev</h1>
        <button onClick={() => setMenuOpen(!menuOpen)}>☰</button>
      </header>

      {/* 메인: 채팅 */}
      <main className="h-[calc(100vh-64px)]">
        <ChatContainer />
      </main>

      {/* 사이드 메뉴 */}
      <HamburgerMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)}>
        <DashboardPanel />
      </HamburgerMenu>
    </div>
  );
}

// 길이: ~30줄 ✅
