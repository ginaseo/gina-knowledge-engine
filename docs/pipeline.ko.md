# 프로세서 파이프라인

```
slack/ (raw)          ─┐
claude-code/ (raw)     ├─→ MarkdownProcessor  →  knowledge/<source>/
                       └─→ WikiProcessor      →  wiki/<source>/

knowledge/<source>/ (slack, claude-code, ...)
  └─→ SummaryProcessor   →  knowledge/summary/

knowledge/summary/
  ├─→ EntityProcessor    →  knowledge/entity/ + projects/ + people/ + wiki/
  ├─→ KeywordProcessor   →  knowledge/keywords/
  └─→ RelatedProcessor   →  knowledge/related/

(항상 실행)
  ├─→ Cleaner            →  잘못되거나 빈 stub 제거
  ├─→ VaultIndexer       →  index/vault_index.json
  └─→ Validator          →  UTF-8 + JSON 유효성 검사
```

## 폴더 구조

```
hermes-knowledge-engine/
├── processor/
│   ├── config.py               # 환경변수 중앙 설정 + fail-fast 검증
│   ├── log.py                  # 로깅 설정 (thread-local 캡처)
│   ├── processing_state.py     # 증분 처리 상태 추적
│   ├── runner.py               # CLI 진입점 (hermes)
│   ├── daemon.py                # 스케줄 작업 실행기 (hermes daemon)
│   ├── history.py              # 작업 실행 이력 저장
│   ├── evaluator.py            # 지식 통계, 품질, health/learning 점수
│   ├── retrieval.py            # 검색 벤치마크 + 질문 생성
│   ├── llm/
│   │   ├── client.py           # OpenAI 호환 LLM 클라이언트
│   │   └── cache.py            # SHA256 키 기반 응답 캐시
│   ├── mcp/
│   │   └── server.py           # Hermes용 MCP 서버 (search/build_context/health)
│   ├── markdown_processor.py
│   ├── wiki_processor.py
│   ├── summary_processor.py
│   ├── entity_processor.py
│   ├── keyword_processor.py
│   ├── related_processor.py
│   ├── validator.py
│   ├── vault_indexer.py
│   └── cleaner.py
├── ingest/
│   └── providers/               # SlackProvider, ClaudeCodeProvider, ...
├── tests/
├── HermesVault/                 # 출력 vault (gitignore 대상)
│   ├── config/
│   │   └── schedule.yaml        # daemon 작업 스케줄
│   ├── index/
│   │   ├── job_history.json     # 작업 실행 이력 (최근 500개 유지)
│   │   └── evaluation_history.json  # 평가 이력 (최근 365개 유지)
│   ├── benchmark/
│   │   └── questions.json       # 자동 생성된 검색 벤치마크 질문
│   └── reports/
│       └── daily-learning.md    # 일일 학습 리포트
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## 증분 처리

각 프로세서는 파일 수정 시각을 `HermesVault/index/<name>_state.json`에 추적합니다.
`mtime`이 바뀐 파일만 재처리됩니다. `--force`로 강제 전체 재처리 가능.

## LLM 캐시

응답은 프롬프트의 SHA256 해시로 `HermesVault/cache/llm_cache.json`에 캐시됩니다.
캐시는 API 호출마다가 아니라 프로세서 실행당 한 번씩 디스크에 기록됩니다.

## Parallel 모드

`--parallel`은 `entity`, `keyword`, `related`를 `ThreadPoolExecutor`로 동시 실행합니다.
콘솔 출력은 스레드별로 버퍼링됐다가 원래 순서대로 flush돼서 섞이지 않습니다.

## Watch 모드

`--watch` (또는 `watch` 서브커맨드)는 일정 주기로 파이프라인을 폴링합니다.
실행 중 처리되지 않은 예외가 나도 에러만 로깅하고 watch 루프는 계속됩니다.
증분 처리 덕분에 매 tick마다 변경된 파일만 처리됩니다.

## Fail-Fast 설정

`HERMES_API_URL`이나 `HERMES_API_KEY`가 없으면 첫 LLM 프로세서 실행 시 명확한
`EnvironmentError`가 발생합니다 — 트레이스백 속에 파묻힌 알 수 없는 API 에러가
아니라. LLM을 호출하지 않는 프로세서(markdown, wiki, cleaner, index, validator)는
자격 증명 없이 실행됩니다. `HERMES_LOCAL_HEURISTIC=1`일 땐 이 검사 자체를
건너뜁니다 — [INSTALL.ko.md](INSTALL.ko.md#로컬-휴리스틱-모드-llm-없이) 참고.

## LLM 백엔드 선택

`LLMClient`(`processor/llm/client.py`)는 인스턴스 생성 시 백엔드를 한 번 정합니다:
기본은 OpenAI 호환 원격 API, `HERMES_LOCAL_HEURISTIC=1`이면
`LocalHeuristicEngine`(`processor/llm/local_engine.py`). LLM 쓰는 4개 프로세서
(summary, entity, keyword, related)와 `DescriptionFillProcessor` 전부 같은
`ask()` 호출을 거치기 때문에 이 프로세서들 입장에서 백엔드 전환은 투명합니다.
`LocalHeuristicEngine.answer()`는 각 프롬프트 템플릿의 고정 문구(주입된 문서
내용 앞부분)를 보고 어느 생성기로 보낼지 판단합니다 — summary/entity/keyword/
related는 `====================` 구분자를 공유하고, `description_fill_prompt.txt`는
`{entity_name}`/`{entity_type}`/`[기존 문서]`/`[새 자료]` 형태가 따로 있어서
그 프롬프트에만 있는 문구로 구분합니다(entity 생성기로 잘못 넘어가지 않게 —
두 프롬프트 다 "Obsidian Knowledge Graph"로 시작해서 문구 하나만으로는
구분 안 됨). 응답 캐시 키는 백엔드+모델별로 네임스페이스가 나뉘어 있어서
이 플래그를 켰다 껐다 해도 다른 백엔드의 캐시된 답이 섞여 나오지 않습니다.
