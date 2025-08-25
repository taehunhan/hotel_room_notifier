# Room Availability Monitor

> 원하는 날짜에 예약 가능한 객실이 생기면 텔레그램으로 알려주는 간단한 모니터링 스크립트입니다. (Agoda/Booking/호텔 공식 사이트 대상)

## 핵심 아이디어
- `sites.json`에 감시할 URL을 넣어두고 주기적으로 실행합니다.
- Playwright(헤드리스 브라우저)로 페이지를 로드하여 실제 화면 텍스트를 분석합니다.
- 상태가 이전 실행과 달라지면 텔레그램으로 알림을 보냅니다.

> **중요**: 각 웹사이트의 서비스 약관(ToS)과 robots.txt를 반드시 확인하고 준수하세요. 자동화/스크래핑이 금지될 수 있습니다.

## 빠른 시작 (로컬 실행)
1) Python 3.10+ 설치
2) 의존성 설치
```bash
pip install -r requirements.txt
python -m playwright install chromium
```
3) 환경 변수 설정
- `.env.example`을 복사해 `.env` 파일 생성 후 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 채웁니다.
- 텔레그램 봇 만들기: @BotFather → 봇 생성 → 채팅방에 초대 → `chat_id`는 @RawDataBot 등으로 확인 가능

4) 모니터링 대상 설정
- `sites.json`에 URL을 원하는 만큼 추가합니다. (아고다/부킹/호텔 공식 사이트 등)
- 동일한 호텔이라도 **날짜/인원/통화/체류일수** 등이 파라미터에 포함되므로, 필요한 조합별로 URL을 넣어두세요.

5) 실행
```bash
python monitor.py
```
- 첫 실행 시 `state.json`이 생깁니다(이전 상태 저장).
- 새로운 실행에서 상태가 변하면 텔레그램 알림이 전송됩니다.

## GitHub Actions로 스케줄 실행 (선택)

`.github/workflows/check.yml`이 포함되어 있습니다. 해당 레포를 비공개로 생성하고 아래를 설정하세요.

- GitHub Repo → Settings → Secrets and variables → Actions
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 추가
- 저장소에 파일 푸시 후, 스케줄에 따라 자동 실행됩니다.

## 크롬 자동화 탐지/로딩 문제
- 대기 시간을 `WAIT_SEC`으로 조정하세요 (기본 22초).
- 간헐적으로 CAPTCHA가 나오거나 동의 배너가 뜰 수 있습니다. 스크립트에서 기본적인 닫기 시도는 하며, 필요한 경우 선택자/대기 로직을 커스터마이즈하세요.
- 요청 빈도는 과도하지 않게(예: 10~30분 간격) 설정하세요.

## 주의사항/한계
- 사이트 UI/문구가 바뀌면 판별 로직이 틀릴 수 있습니다.
- 일부 사이트는 API 호출에 기반한 더 정교한 방법이 가능하지만, 약관을 위반할 수 있으니 주의하세요.
- 상업적 사용이나 대량 모니터링은 권장하지 않습니다.

## 커스터마이즈 포인트
- `KO_PATTERNS_AVAILABLE`/`KO_PATTERNS_SOLDOUT`을 필요에 맞게 보강
- Slack/Webhook/Email 알림 추가
- 특정 객실 타입/가격 임계값 필터링 등
