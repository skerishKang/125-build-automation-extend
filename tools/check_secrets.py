#!/usr/bin/env python3
"""
민감한 파일 보호 스크립트
수동으로 실행하거나 CI/CD 파이프라인에서 사용
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# 보호할 민감 파일 패턴
SENSITIVE_PATTERNS = [
    r'\.env$',
    r'gmail_credentials\.json$',
    r'service_account\.json$',
    r'telegram-google\.json$',
    r'gmail_token\.pickle$',
    r'gmail_token\.json$',
    r'token\.pickle$',
    r'bots/\.env$',
    r'.*secret.*\.json$',
    r'.*credentials.*\.json$',
    r'.*token.*\.json$'
]

# 백업 디렉터리
BACKUP_DIR = Path("secrets_backup")

class SecretChecker:
    def __init__(self):
        self.violations = []

    def check_file(self, file_path):
        """파일 하나 검사"""
        file_path = Path(file_path)

        # Skip non-existent files
        if not file_path.exists():
            return

        # Skip .git directory
        if '.git' in str(file_path):
            return

        # 패턴 매칭
        for pattern in SENSITIVE_PATTERNS:
            if file_path.match(pattern):
                self.violations.append(str(file_path))
                print(f"[SECURITY] Sensitive file found: {file_path}")

                # 백업 확인
                if BACKUP_DIR / file_path.name != file_path:
                    print(f"[WARNING] Consider backing up to: {BACKUP_DIR / file_path.name}")
                return

    def check_all_files(self):
        """모든 파일 검사"""
        print("=" * 60)
        print("[CHECK] Sensitive File Security Scan")
        print("=" * 60)

        # 현재 디렉터리에서 재귀적으로 파일 검사
        for root, dirs, files in os.walk('.'):
            # .git 디렉터리 스킵
            if '.git' in root:
                continue

            for file in files:
                file_path = os.path.join(root, file)
                self.check_file(file_path)

        if self.violations:
            print("\n" + "=" * 60)
            print(f"[ALERT] {len(self.violations)} sensitive files found!")
            print("=" * 60)
            for v in self.violations:
                print(f"   - {v}")
            print("\n[SOLUTION]")
            print("   1. Check if pattern is in .gitignore")
            print("   2. If already committed: git rm --cached <file>")
            print("   3. If accidentally modified: git checkout HEAD -- <file>")
            print("   4. For permanent protection: echo <file> >> .git/info/exclude")
            return False
        else:
            print("[SUCCESS] All files are secure!")
            return True

    def create_backup(self, file_path):
        """백업 생성"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        BACKUP_DIR.mkdir(exist_ok=True)

        # SHA256 해시 계산
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        backup_path = BACKUP_DIR / f"{file_path.name}.{file_hash[:8]}"

        # 백업 생성
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"[SUCCESS] Backup created: {backup_path}")

        return True

def main():
    checker = SecretChecker()
    safe = checker.check_all_files()

    # 백업 디렉터리 생성 및 권장사항 제공
    BACKUP_DIR.mkdir(exist_ok=True)
    print(f"\n[INFO] Backup directory: {BACKUP_DIR.absolute()}")
    print("   Manually backup files that need to be secured")

    # 종료 코드
    sys.exit(0 if safe else 1)

if __name__ == "__main__":
    main()
