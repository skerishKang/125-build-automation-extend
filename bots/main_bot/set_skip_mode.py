#!/usr/bin/env python3
"""자동으로 모드를 'skip'으로 설정하는 스크립트"""
import sys
import os
import json

# .env 파일에서 CHAT_ID 읽어오기
chat_id = None
if os.path.exists('bots/.env'):
    with open('bots/.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('TELEGRAM_CHAT_ID='):
                chat_id = line.split('=', 1)[1].strip()
                break

if not chat_id:
    print("❌ TELEGRAM_CHAT_ID를 bots/.env에서 찾을 수 없습니다.")
    print("봇과 대화해서 CHAT_ID를 확인하세요.")
    sys.exit(1)

# preference_store에서 모드 변경
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bots.shared.user_preferences import preference_store

try:
    # 현재 설정 읽기
    current_prefs = preference_store.get_preferences(chat_id)
    print(f"📖 현재 설정: {current_prefs}")
    
    # 모드를 'skip'으로 변경
    new_prefs = preference_store.set_preferences(chat_id, {"mode": "skip"})
    
    # 변경된 설정 출력
    updated_prefs = preference_store.get_preferences(chat_id)
    print(f"✅ 모드가 'skip'으로 변경되었습니다!")
    print(f"📖 새로운 설정: {updated_prefs}")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    sys.exit(1)
