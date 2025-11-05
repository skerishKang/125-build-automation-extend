#!/usr/bin/env python3
import os
import re

emoji_map = {
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '🤖': '[BOT]',
    '📋': '[DOC]',
    '🎤': '[AUDIO]',
    '🖼️': '[IMAGE]',
    '💬': '[CHAT]',
    '📄': '[FILE]',
    '🟢': '[GREEN]',
    '👋': 'BYE',
    '🔍': '[VIEW]',
    '📊': '[STATS]',
    '📡': '[SIGNAL]',
    '🚀': '[RUN]',
    '💡': '[TIP]'
}

def fix_emojis_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for emoji, replacement in emoji_map.items():
        if emoji in content:
            content = content.replace(emoji, replacement)
            modified = True
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed emojis in: {filepath}")
        return True
    return False

bot_files = [
    'main_bot/main_bot.py',
    'document_bot/document_bot.py',
    'audio_bot/audio_bot.py',
    'image_bot/image_bot.py',
    'run_bots.py'
]

for bot_file in bot_files:
    if os.path.exists(bot_file):
        fix_emojis_in_file(bot_file)

print("Done!")
