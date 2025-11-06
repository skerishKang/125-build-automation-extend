"""
Test Google Drive Connection
"""
import os
import sys

# Add backend to path
sys.path.insert(0, 'backend')

try:
    from services.google_drive import get_drive_service, list_files, upload_file
    from services.drive_sync import FOLDER_ID
    import tempfile

    print("🔍 Google Drive 연결 테스트 시작...\n")

    # Get service
    print("1. 서비스 계정 인증 중...")
    service = get_drive_service()
    print("   ✅ 인증 성공!\n")

    # List files
    print("2. 폴더 파일 목록 조회 중...")
    folder_id = os.getenv("DRIVE_SUMMARY_FOLDER_ID") or FOLDER_ID
    files = list_files(folder_id=folder_id, max_results=10)
    print(f"   ✅ 폴더에 {len(files)}개 파일이 있습니다.\n")

    # Show files
    print("3. 파일 목록:")
    for i, file in enumerate(files, 1):
        print(f"   {i}. {file.get('name', 'N/A')} (ID: {file.get('id', 'N/A')[:20]}...)")

    print("\n✅ Google Drive 연결이 정상적으로 작동합니다!")
    print(f"   폴더 ID: {folder_id}")

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    print("\n💡 해결 방법:")
    print("   1. service_account.json 파일이 backend/ 폴더에 있는지 확인")
    print("   2. Google Drive 폴더에 서비스 계정 이메일이 공유되었는지 확인")
    print("      이메일: telegramgd@gen-lang-client-0470100677.iam.gserviceaccount.com")
    print("   3. 권한이 '편집자' 또는 '사용자'로 설정되어 있는지 확인")
