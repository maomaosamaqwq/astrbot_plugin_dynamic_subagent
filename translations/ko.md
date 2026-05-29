# 🐾 Dynamic SubAgent — 한국어

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

메인 AI 에이전트가 서브 에이전트를 동적으로 생성하고 관리할 수 있는 AstrBot 플러그인입니다. **권한 격리**와 **중첩 깊이 제한**으로 안전한 멀티 에이전트 시스템을 구현합니다.

## ✨ 특징

| 특징 | 설명 |
|------|------|
| 🧠 동적 생성 | `spawn_agent`로 서브 에이전트를 온디맨드 생성 (권한/모델/영속성 지정 가능) |
| 🔄 작업 전달 | `transfer_to_agent`로 기존 서브 에이전트에 작업 위임 |
| 🔒 권한 격리 | `safe` / `medium` / `full` 3단계 권한 — 서브 에이전트는 승격 불가 |
| 🛡 깊이 제한 | 서브 에이전트는 서브 에이전트를 생성할 수 없음, 무한 체인 방지 |
| 💾 영속 메모리 | 영속 에이전트는 재시작 후에도 컨텍스트 유지 + 이력 주입 |
| 🕥 협력 추적 | spawn/transfer 체인의 완전한 추적 및 보고서 |

## ⚙️ 권한 체계

| 레벨 | 내장 도구 | 플러그인 도구 | spawn 가능 | 설명 |
|:----:|:---------:|:-----------:|:----------:|------|
| `safe` | ❌ | 화이트리스트 | ❌ | 검색+관리만 |
| `medium` | 파일 R/W | 블랙리스트 | ❌ | shell/python 없음 |
| `full` | ✅ 전체 | ✅ 전체 | ❌ | 메인 에이전트와 동일 |

> 서브 에이전트는 Python/IPython 실행기를 사용할 수 없으며, 서브 에이전트를 생성할 수 없습니다.

## 📦 설치

AstrBot 플러그인 마켓플레이스에서 `dynamic_subagent`를 검색하거나 수동으로 클론:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 빠른 시작

```python
# 1. 즉시 작업이 있는 서브 에이전트 생성
spawn_agent(
    name="code_reviewer",
    description="코드 리뷰 어시스턴트",
    permission_level="medium",
    task="다음 코드를 리뷰해 주세요: ..."
)

# 2. 영속 서브 에이전트 생성, 나중에 작업 전달
spawn_agent(
    name="memory_bot",
    description="대화를 기억하는 어시스턴트",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="이전 주제를 계속해 주세요..."
)

# 3. 협력 보고서 보기
show_collaboration_report()
```

## ⚙️ 설정

| 설정 항목 | 기본값 | 설명 |
|-----------|:------:|------|
| `max_spawns_per_event` | `10` | 전역 서브 에이전트 생성 제한 |
| `max_handoffs_per_event` | `20` | 전역 작업 전달 제한 |
| `max_context_turns` | `20` | 영속 에이전트가 유지하는 컨텍스트 턴 수 |
| `trace_enabled` | `true` | 협력 추적 활성화 |
| `model_blacklist` | `[]` | 사용 금지 모델 목록 |
| `model_filter_mode` | `blacklist` | 모델 필터 모드 (blacklist/whitelist) |
| `allowed_models` | `[]` | 화이트리스트 모드 시 허용 모델 목록 |

## 🏗 아키텍처

```
메인 에이전트 (depth=0, full)
 └─ spawn_agent() → 서브 에이전트 (depth=1, safe/medium/full)
     └─ transfer_to_agent() → 서브 에이전트가 작업 실행
         └─ ❌ spawn 불가 (depth>=1 차단)
```

- **중첩 깊이**: 메인 에이전트 depth=0, 서브 에이전트 depth=1 — 추가 중첩 불가
- **권한 상속**: 생성자 권한 ≥ 대상 권한 (medium은 full 생성 불가)
- **도구 격리**: `_build_sub_tools`에서 서브 에이전트 도구 구성, depth≥1에서 spawn/delete 자동 제거

## 📝 라이선스

MIT

---
*이 소개는 한국어로 작성되었습니다.*
