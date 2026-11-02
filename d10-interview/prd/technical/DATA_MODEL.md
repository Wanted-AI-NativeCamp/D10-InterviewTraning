# 데이터 모델 및 Markdown 내보내기 명세

## 1. 핵심 엔터티

  ------------------------------------------------------------------------
  엔터티                  필수 키/필드             관계
  ----------------------- ------------------------ -----------------------
  Project                 `project_id`, `title`    ExperienceCard 1:N

  ExperienceCard          `experience_id`,         ExperienceVersion 1:N
                          `project_id`,            
                          `current_version`,       
                          `status`                 

  ExperienceVersion       `experience_id`,         불변 기록
                          `version`,               
                          `content_snapshot`,      
                          `created_at`             

  Company                 `company_id`, `name`,    InterviewSession 1:N
                          `role`, `priority`,      
                          `application_status`     

  Schedule                `schedule_id`,           회사 일정
                          `company_id`, `type`,    
                          `date`                   

  InterviewSession        `session_id`,            InterviewAnswer 1:N
                          `company_id?`, `role`,   
                          `status`, `started_at`   

  Question                `question_id`, `type`,   질문 데이터
                          `competencies`,          
                          `rubric_version`         

  InterviewAnswer         `answer_id`,             Evaluation 1:N
                          `session_id`,            
                          `question_id`,           
                          `experience_id?`,        
                          `experience_version?`,   
                          `answer_text`,           
                          `reference_used`         

  Evaluation              `evaluation_id`,         불변
                          `answer_id`,             
                          `answer_snapshot`,       
                          `experience_snapshot`,   
                          `rubric_version`,        
                          `scores`, `reasons`,     
                          `created_at`             

  Quest                   `quest_id`, `type`,      독립 데이터
                          `experience_id?`,        
                          `answer_id?`,            
                          `company_id?`, `status`  
  ------------------------------------------------------------------------

`?`는 선택값. 회사 미등록 면접, 경험 미선택 답변 허용.

## 2. 버전/평가 보존 (`DATA-01`)

-   경험 수정은 새 ExperienceVersion 생성 후 카드의 `current_version`
    갱신.
-   InterviewAnswer는 **답변 제출 당시**의 `experience_version` 참조.
-   Evaluation에는 질문, 답변 텍스트, 경험 정보, 평가 루브릭 버전의
    스냅샷 저장.
-   이후 경험 수정, 질문 태그 변경, 평가 모델 변경이 과거 결과에 영향을
    주지 않음.
-   재평가 시 새 Evaluation 생성; 기존 결과 덮어쓰기 금지.

## 3. 앱 내부 저장과 파일 내보내기 구분 (`DATA-02`)

-   **내부 저장:** 사용자 작업 상태를 유지하는 영속 저장(구현 방식 팀
    결정).
-   **Markdown 내보내기:** 현재 저장된 데이터의 휴대용 스냅샷 다운로드.
-   `.md` 다운로드가 앱 내부 저장을 대신하지 않는다.
-   Markdown **가져오기(import)**는 기존 프로토타입 호환성 검토 대상; 새
    형식의 완전한 역직렬화는 P1로 둔다.

## 4. 내보내기 유형

  ---------------------------------------------------------------------------------------
  ID                모드              포함                              허용 시점
  ----------------- ----------------- --------------------------------- -----------------
  `EXPOR-01`        경험 관리만       프로젝트, 경험 카드,              면접 0건/작성
                                      버전·상태·태그, 선택적 퀘스트     중에도

  `EXPOR-02`        경험+면접 통합    경험 데이터 +                     면접 전·중·후
                                      회사/세션/질문/답변/평가/퀘스트   

  `EXPOR-03`        면접만(기존 호환) 선택한 면접 세션·답변·평가        진행 중/완료(기존
                                                                        정책과 충돌 시
                                                                        명시)
  ---------------------------------------------------------------------------------------

## 5. 공통 출력 규칙 (`EXPOR-04`)

-   UTF-8 `.md`, ISO 8601 내보낸 시각, `schema_version`, export mode,
    원본 ID.
-   범위 선택: 경험 전체/프로젝트별; 통합 시 회사별/세션별/전체.
-   파일명 예: `yeokjeon-experiences-2026-11-01.md`,
    `yeokjeon-full-company-2026-11-01.md`.
-   빈 필드는 `미작성`, 진행 중 세션은 `진행 중`, 평가 전은 `평가 대기`
    표시.
-   미제출 답변 초안은 기본 제외; 포함 시 '미제출 초안' 명시하고 사용자
    동의.
-   중복 경험은 통합 문서의 경험 섹션에 한 번만 기록하고 답변에서 ID로
    참조.
-   Markdown 텍스트에 포함된 특수 문자·사용자 입력 제목은 안전하게
    이스케이프/정규화.
-   다운로드 전에 선택 범위와 개인정보 포함 여부를 보여준다.
-   내보내기 실패는 내부 저장 데이터에 영향을 주지 않는다.

## 6. 경험만 내보내기 예시

``` markdown
---
schema_version: "2.1"
export_mode: "experience_only"
exported_at: "2026-11-01T17:00:00+09:00"
---

# 경험 관리 내보내기

## 프로젝트: 동행
- 프로젝트 ID: PRJ-001

### 경험: 캘린더 구현 방향 조율
- 경험 ID: EXP-001
- 버전: 2
- 상태: 정리 완료
- 역량: 협업, 의사결정

#### 상황
모바일 앱 캘린더 구현 방향에 대한 의견 차이가 있었다.

#### 나의 행동
사용자 흐름과 화면 기획을 공유하며 구현 방향을 조율했다.

#### 판단 근거
모바일 사용성과 개발 부담을 고려했다.

#### 결과
일별·월별 보기 중심으로 구현 방향을 조정했다.
```

## 7. 통합 내보내기 예시

``` markdown
---
schema_version: "2.1"
export_mode: "full"
exported_at: "2026-11-01T17:00:00+09:00"
---

# 역전 면접 코칭 — 통합 기록

## 1. 프로젝트 및 경험
(경험만 내보내기와 동일한 형식)

## 2. 지원 회사
- 회사 ID: COM-001
- 회사명: 예시 회사
- 직무: UX/UI 디자이너
- 지망: 1지망
- 지원 상태: 면접 예정

## 3. 면접 세션
- 세션 ID: SES-001
- 상태: 진행 중
- 진행: 2/5문항

### 질문 1
- 질문 ID: Q-001
- 선택 경험: EXP-001 (v2)
- 경험 참고: 예
- 답변: ...
- 꼬리질문: ...
- 평가: 평가 대기

### 질문 2
- 상태: 미응답

## 4. 강화 퀘스트
- 유형: 전달 강화
- 연결 경험: EXP-001
- 상태: 진행 중
```

## 8. 저장 정책 결정 사항

-   실제 DB/파일 저장소 선택.
-   자동저장 주기 및 오프라인 동작.
-   소프트 삭제 및 개인정보 보존 기간.
-   구형 Markdown import 파서 지원 범위.
-   내보내기 파일 암호화 여부(기본 Markdown은 암호화되지 않음).

## 9. 완료 기준

-   면접 없는 경험 데이터의 단독 내보내기 성공.
-   진행 중 면접 포함 통합 내보내기 성공.
-   내보내기 후에도 편집 중 데이터/내부 저장 불변.
-   경험 수정 후 이전 평가 스냅샷 유지.
-   파일 재열람 시 ID, 버전, 상태, 질문·답변 관계를 식별 가능.
