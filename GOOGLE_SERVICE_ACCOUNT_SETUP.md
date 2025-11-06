# Google Drive 서비스 계정 설정 가이드

## 📋 필요한 파일 생성하기

### 1. Google Cloud Console에서 서비스 계정 키 생성

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/ 접속

2. **프로젝트 선택** (기존 프로젝트 사용하거나 새 프로젝트 생성)

3. **IAM 및 관리자 → 서비스 계정** 이동
   - https://console.cloud.google.com/iam-admin/serviceaccounts

4. **"+ 서비스 계정 만들기" 클릭**

5. **서비스 계정 정보 입력**
   ```
   이름: drive-bot-service
   설명: Google Drive 파일 업로드용 서비스 계정
   ```

6. **권한 부여**
   - 역할 선택: `편집자 (Editor)` 또는 `Cloud Storage Admin`

7. **키 생성**
   - "키" 탭 클릭
   - "키 추가" → "새 키" 클릭
   - JSON 형식 선택 후 다운로드

8. **다운로드된 파일을 다음 위치에 저장**
   ```
   backend/service_account.json
   ```

### 2. Google Drive 공유 폴더 권한 부여

서비스 계정이 Google Drive 폴더에 접근할 수 있도록 권한을 부여해야 합니다.

1. **Google Drive에서 폴더 열기**
   ```
   https://drive.google.com/drive/folders/19hVkhtfoX1s7EVzoeuc8bvo2mosBJg75
   ```

2. **폴더 공유 설정**
   - 폴더를 마우스 오른쪽 클릭
   - "공유" 선택
   - "링크가 있는 모든 사용자" 또는 "제한"中选择

3. **서비스 계정 이메일 추가**
   - 다운로드한 JSON 파일에서 `client_email` 확인
   - 예: `drive-bot-service@your-project.iam.gserviceaccount.com`
   - 이 이메일을 파일 공유에 추가
   - 권한: "편집자" 또는 "사용자"

### 3. bot 재시작

```bash
# bots 가상환경 활성화
# (기존 실행 방식대로)
```

## 🔒 보안 참고사항

- `service_account.json` 파일은 절대 GitHub에 업로드하지 마세요
- `.gitignore`에 이미 추가되어 있습니다
- API 키나 비밀번호와 같은 민감한 정보입니다

## ✅ 확인 방법

서비스 계정이 제대로 설정되었는지 확인:
```bash
cd backend
python -c "
from services.google_drive import get_drive_service, list_files
try:
    service = get_drive_service()
    files = list_files(folder_id='19hVkhtfoX1s7EVzoeuc8bvo2mosBJg75')
    print(f'✅ Google Drive 연결 성공! 폴더 파일 수: {len(files)}')
except Exception as e:
    print(f'❌ 오류: {e}')
"
```
