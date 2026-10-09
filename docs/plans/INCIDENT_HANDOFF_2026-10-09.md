# Waterbe 장애 대화 인계 기록 — 2026-10-09

이 기록은 [중앙 관리 지침](../guides/THINKPAD_CENTRAL_MANAGEMENT_GUIDE.md)의
`장애 대응 담당 — 2026-10-09 사용자 지정` 절차에 연결한다.

## 구현 범위

- 기존 `cas-telegram-reporter`가 Telegram API의 수락을 확인한 사건만
  `incident-handoff/pending/<incident-id>.json`에 보존한다. `delivery_uncertain`은
  인계하거나 재전송하지 않는다.
- 기존 `terminal-bot-waterbe`는 인증된 사용자의 다음 메시지가 있을 때만 하나의
  봉투를 원자적으로 임대해 기존 tmux `waterbe` 세션에 붙인다. 봉투의 외부 요약은
  신뢰할 수 없는 상태 정보이며 새 권한·명령이 아니다.
- 최종 응답이 Telegram에 수락되고 세션이 ready 상태일 때만 `completed`로 옮긴다.
  세션 무응답·한도·프로세스 재시작에는 임대를 보존하고, 15분 뒤 다음 사용자 메시지에서
  다시 제시한다. 백그라운드 재시도·새 Codex·자동 복구는 없다.

## 2026-10-09 확인 증거

- reporter 단위 시험 29건 통과: 수락 알림만 인계하고 네트워크 미확정 건은 인계하지
  않는 조건을 포함한다.
- 단발성 안전 시험 알림은 Telegram API 수락을 받았고, 자동 조치 금지 인계 봉투가
  생성됐다. 저울 제어·데이터 변경은 수행하지 않았다.
- 브리지 격리 시험에서 원자 임대→완료와 만료 임대→재보류를 확인했다.
- `terminal-bot-waterbe.service`는 `Restart=always`로 활성 상태다.

## 보류와 안전 조치

- reporter의 기존 알림 대상과 Waterbe 브리지의 마지막 보존 대화 ID가 일치하지 않아,
  사용자가 실제 Telegram Waterbe 대화에서 답하고 같은 대화로 응답을 받는 종단 증거는
  아직 없다. 이를 완료로 표시하지 않는다.
- 설치 직후 기존 과거 운영 이벤트 520건이 reporter 대기열에 발견됐다. 알림 폭주를
  막기 위해 reporter timer는 중지했으며, 대기열과 전달 미확정 1건은 삭제·재전송하지
  않았다. 현행 정책을 재개하기 전 원본별 유효성 및 과거 이벤트 처리 정책을 별도로
  사용자와 확인한다.
