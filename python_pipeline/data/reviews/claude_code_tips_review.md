    # claude_code_tips 배치 리뷰

실행 파일
- url_list: python_pipeline/data/url_lists/claude_code_tips.txt
- raw: python_pipeline/data/raw/raw_from_urls_claude_code_tips.json
- cards: python_pipeline/data/cards/cards_raw_from_urls_claude_code_tips.json

## 카드 판정

### 1번 카드
- 제목: I benchmarked "Plan with Opus, Execute with Codex" — here's the actual cost data
- 판정: 좋은 카드
- publish 후보: 예
- 이유: 실측 비용 비교, crossover 기준, cache reads 인사이트가 남음

### 2번 카드
- 제목: I'm new to Claude Code...
- 판정: 좋은 카드
- publish 후보: 보류
- 이유: 본문은 약하지만 댓글에서 학습 경로와 실전 팁이 살아남

### 3번 카드
- 제목: I built an AI job search system with Claude Code...
- 판정: 좋은 카드
- publish 후보: 조건부 예
- 이유: 오픈소스 사례와 기능 설명은 좋지만 제목 오해 보정 필요

## 배치 회고
- 잘 먹힌 유형:
- 약했던 유형:
- 다음 배치에서 더 넣을 유형:
- 다음 배치에서 줄일 유형: