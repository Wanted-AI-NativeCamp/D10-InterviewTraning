# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import html
import itertools
import json
import math
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import altair as alt
import pandas as pd
import streamlit as st

import coach
from llm import LLMError, ask_json
from prompts import (
    EVAL_SCHEMA,
    FIELDS,
    HIGHLIGHT_SCHEMA,
    INTERVIEWER_SCHEMA,
    LAST_QUESTION_SCHEMA,
    LAST_SUGGEST_INPUT,
    LAST_SUGGEST_SCHEMA,
    PANEL_CRITERIA,
    PERSONA_CARDS,
    PERSONA_TAGS,
    PERSONAS,
    RETRY_SCHEMA,
    STRATEGY_SCHEMA,
)

st.set_page_config(  # 파비콘: assets/favicon.png (원본 fabicon.png 를 256px 로 줄인 것)
    page_title="역전 면접 코칭",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "favicon.png"),
)


def hover_css() -> str:
    """호버를 한 가지로: 주 버튼은 마우스를 올려도 색이 그대로, 나머지 버튼 · 태그는 글자색 그대로 + 아주 옅은 바탕.
    탭은 호버 때 글자색이 바뀌지 않게. (Streamlit 기본은 버튼 종류마다 하늘색 · 회색 · 진한 색으로 제각각)
    고른 탭은 Streamlit 기본 밑줄 그대로 (채운 바탕은 위쪽 모서리 둥글리기를 보장할 수 없어서 쓰지 않는다).
    코드 칸(리포트 미리보기)의 마크다운 제목은 Streamlit 기본이 빨강(.token.important)이라 강조색으로.
    다크에서는 글자라서 강조색(#4263D6, 바탕 대비 3.2)보다 밝은 같은 계열(config.toml linkColor #9DB0F0)을 쓴다."""
    dark = getattr(st.context.theme, "type", None) == "dark"
    accent = "#4263D6" if dark else "#10256B"  # config.toml 강조색과 같게
    heading = "#9DB0F0" if dark else "#10256B"
    # 타이틀 화면 판: 라이트는 화이트 → 아이스 블루, 다크는 어두운 남색 (다크 바탕에 흰 판은 눈부셔서)
    if dark:
        title = {"bg": "radial-gradient(ellipse at 50% 30%, #16307F 0%, #0A1030 45%, #05070F 100%)",
                 "bar": "linear-gradient(90deg, #05070F, #16307F 50%, #05070F)", "border": "transparent",
                 "text": "#C2C4C8", "caption": "#878A93", "glow": "rgba(66, 99, 214, 0.55)",
                 "sub_bg": "rgba(255, 255, 255, 0.04)", "sub_border": "rgba(157, 176, 240, 0.55)", "sub_text": "#E8EBF5",
                 "sub_hover": "rgba(157, 176, 240, 0.14)", "focus": "#9DB0F0",
                 "head": "#E8EBF5", "haze1": "rgba(66, 99, 214, 0.35)", "haze2": "rgba(157, 176, 240, 0.18)"}
    else:
        title = {"bg": "linear-gradient(180deg, #FFFFFF 0%, #EEF6FF 50%, #D6EAFB 100%)",
                 "bar": "linear-gradient(90deg, #FFFFFF, #E3F0FD 50%, #FFFFFF)", "border": "#D6E4F2",
                 "text": "#46474C", "caption": "#5A5C63", "glow": "rgba(31, 37, 92, 0.25)",
                 "sub_bg": "#FFFFFF", "sub_border": "#B9C6F2", "sub_text": "#10256B",
                 "sub_hover": "#EEF3FF", "focus": "#10256B",
                 "head": "#10256B", "haze1": "rgba(255, 255, 255, 0.9)", "haze2": "rgba(110, 170, 235, 0.5)"}
    return f"""<style>
[data-testid="stCode"] .token.important, [data-testid="stCode"] .token.title {{ color: {heading} !important; }}
[data-testid="stBaseButton-primary"]:hover:not(:disabled),
[data-testid="stBaseButton-primary"]:focus-visible {{
  background-color: {accent} !important; border-color: {accent} !important; color: #FFFFFF !important; }}
[data-testid^="stBaseButton-"]:not([data-testid="stBaseButton-primary"]):not([data-testid$="Active"]):hover:not(:disabled) {{
  background-color: color-mix(in srgb, currentColor 6%, transparent) !important; color: inherit !important; }}
[data-testid="stTabs"] [role="tab"]:not([aria-selected="true"]):hover {{ color: inherit !important; }}
/* 평가 탭 회차 태그: 헬스케어(blue 배지)는 하늘색. 테마 blue(진 네이비)와 구분 — 글자색 값으로 찾는다 (config.toml blueTextColor) */
[data-testid="stExpander"] summary .stMarkdownBadge[style*="color: rgb(16, 37, 107)"],
.st-key-eval_legend .stMarkdownBadge[style*="color: rgb(16, 37, 107)"],
.st-key-memo_qcard .stMarkdownBadge[style*="color: rgb(16, 37, 107)"] {{
  background-color: #E0F2FE !important; color: #0369A1 !important; }}
[data-testid="stExpander"] summary .stMarkdownBadge[style*="color: rgb(185, 198, 242)"],
.st-key-eval_legend .stMarkdownBadge[style*="color: rgb(185, 198, 242)"],
.st-key-memo_qcard .stMarkdownBadge[style*="color: rgb(185, 198, 242)"] {{
  background-color: #0B3049 !important; color: #7DD3FC !important; }}
/* 헤더 아래 간격: Streamlit 기본은 본문 위쪽 여백 96px (헤더 60px + 빈 공간 36px) → 76px (빈 공간 16px).
   헤더가 본문 위에 떠 있어서 60px 보다 줄이면 맨 위 내용이 헤더에 가려진다 */
[data-testid="stMainBlockContainer"] {{ padding-top: 76px !important; }}
/* 글자 체계: 당근(about.daangn.com) 줄간격 · 자간 (크기 · 굵기는 config.toml headingFontSizes · headingFontWeights)
   H1 42/58 · H2 28/42 · H3 20/28 · 본문 16/24, 제목 자간 -0.6px. 좁은 화면에서 H1 은 30px 로 */
[data-testid="stHeading"] h1, [data-testid="stMarkdownContainer"] h1 {{ line-height: 1.38 !important; letter-spacing: -0.6px; }}
[data-testid="stHeading"] h2, [data-testid="stMarkdownContainer"] h2 {{ line-height: 1.5 !important; letter-spacing: -0.6px; }}
[data-testid="stHeading"] h3, [data-testid="stMarkdownContainer"] h3 {{ line-height: 1.4 !important; letter-spacing: -0.4px; }}
[data-testid="stMarkdownContainer"] p {{ line-height: 1.5; }}
@media (max-width: 640px) {{ [data-testid="stHeading"] h1 {{ font-size: 30px !important; }} }}
/* 타이틀 화면: 게임 첫 화면처럼 로고 + 메뉴 (색은 위 title 값 · 라이트/다크) */
.st-key-title_screen {{ background: {title["bg"]}; border: 1px solid {title["border"]};
  border-radius: 16px; padding: 56px 24px 40px; min-height: 72vh; justify-content: center; align-items: center; gap: 12px;
  position: relative; overflow: hidden; }}
/* 스플래시 (들어올 때 한 번): 로고는 홈 화면 로고 하나를 그대로 쓰고 움직이지 않는다.
   로고 아래 칸(title_stage)에 스플래시 문구와 홈 내용(title_body)을 같은 자리에 겹쳐 두어, 칸 높이가 변하지 않으니
   문구가 홈 내용으로 바뀌어도 로고 위치가 그대로다. 아지랑이는 판 뒤에서만 피어오르다 걷힌다. CSS 만 쓴다.
   시간: 문구 0.5s~ 떠오름 · 2.5s~ 걷힘 · 아지랑이 3.0s~ 걷힘 · 홈 내용 3.0s~ 나타남 */
.st-key-title_screen > * {{ position: relative; z-index: 1; }}
.st-key-title_stage {{ display: grid !important; grid-template-columns: minmax(0, 1fr); width: 100%; }}
.st-key-title_stage > * {{ grid-area: 1 / 1; min-width: 0; width: 100% !important; justify-self: stretch; }}
.st-key-title_body, .st-key-splash_text {{ align-items: center; width: 100% !important; gap: 12px; }}
.st-key-title_body > *, .st-key-splash_text > * {{ max-width: 100%; }}
.st-key-splash_text {{ align-self: start; gap: 4px; padding-top: 4px; animation: content-out 0.5s ease-in 2.5s forwards; }}
.st-key-title_stage:has(.st-key-splash_text) .st-key-title_body {{ animation: body-in 0.6s ease-out 3.0s both; }}
.st-key-title_screen:has(.st-key-splash_text)::before, .st-key-title_screen:has(.st-key-splash_text)::after {{
  content: ""; position: absolute; left: -20%; right: -20%; bottom: -35%; height: 90%;
  background: radial-gradient(ellipse 30% 45% at 25% 70%, {title["haze1"]}, transparent 70%),
              radial-gradient(ellipse 25% 40% at 72% 75%, {title["haze2"]}, transparent 70%),
              radial-gradient(ellipse 35% 35% at 50% 88%, {title["haze1"]}, transparent 70%);
  filter: blur(14px); pointer-events: none; z-index: 0; transform-origin: 50% 100%;
  animation: haze-rise 3.4s ease-in-out infinite, content-out 0.8s ease-in 3.0s forwards; }}
.st-key-title_screen:has(.st-key-splash_text)::after {{ animation-duration: 4.2s, 0.8s; animation-delay: -1.7s, 3.0s; }}
.st-key-splash_head, .st-key-splash_sub {{ align-items: center; }}
/* 로고: 자리는 그대로 두고 투명도만 0 → 1 로 서서히 (스플래시 때만) */
.st-key-title_screen:has(.st-key-splash_text) img {{ animation: logo-fade 1s ease-out both; }}
.st-key-splash_head {{ animation: text-in 0.8s ease-out 0.5s both; }}
.st-key-splash_sub {{ animation: text-in 0.8s ease-out 0.8s both; }}
.st-key-title_screen .st-key-splash_head [data-testid="stMarkdownContainer"] p {{
  font-size: 1.4rem; font-weight: 700; color: {title["head"]} !important; text-align: center; word-break: keep-all; }}
.st-key-title_screen .st-key-splash_sub [data-testid="stMarkdownContainer"] p {{
  font-size: 1rem; color: {title["text"]} !important; text-align: center; word-break: keep-all; }}
@keyframes haze-rise {{
  0% {{ transform: translateY(35%) scaleX(1) skewX(0deg); opacity: 0; }}
  30% {{ opacity: 1; }}
  50% {{ transform: translateY(0) scaleX(1.08) skewX(4deg); }}
  100% {{ transform: translateY(-55%) scaleX(0.95) skewX(-3deg); opacity: 0; }} }}
@keyframes logo-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes text-in {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes content-out {{ to {{ opacity: 0; visibility: hidden; }} }}
@keyframes body-in {{ from {{ opacity: 0; visibility: hidden; }} to {{ opacity: 1; visibility: visible; }} }}
/* 움직임 줄이기 설정: 아지랑이 없이 문구만 잠깐 보였다가 바로 홈 내용 */
@media (prefers-reduced-motion: reduce) {{
  .st-key-title_screen:has(.st-key-splash_text)::before, .st-key-title_screen:has(.st-key-splash_text)::after {{ display: none; }}
  .st-key-splash_head, .st-key-splash_sub, .st-key-title_screen:has(.st-key-splash_text) img {{ animation: none; }}
  .st-key-splash_text {{ animation-duration: 0.01s; animation-delay: 1.8s; }}
  .st-key-title_stage:has(.st-key-splash_text) .st-key-title_body {{ animation-duration: 0.01s; animation-delay: 1.8s; }} }}
.st-key-title_screen img {{ display: block; margin: 0 auto 32px; max-width: min(560px, 100%) !important; height: auto; }}
.st-key-title_screen [data-testid="stMarkdownContainer"] p {{ color: {title["text"]} !important; text-align: center; word-break: keep-all; }}
.st-key-title_screen [data-testid="stCaptionContainer"], .st-key-title_screen [data-testid="stCaptionContainer"] p {{
  color: {title["caption"]} !important; text-align: center; word-break: keep-all; }}
.st-key-title_menu {{ width: min(340px, 100%) !important; align-self: center; gap: 12px; margin: 20px auto 8px; }}
.st-key-title_screen .st-key-title_menu button [data-testid="stMarkdownContainer"] p {{ color: inherit !important; }}  /* 버튼 글자는 버튼 색 그대로 */
.st-key-title_menu button {{ min-height: 56px; }}
.st-key-title_menu button p {{ font-size: 1.05rem !important; font-weight: 600; }}
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-primary"],
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-primary"]:hover:not(:disabled),
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-primary"]:focus-visible {{
  background-color: #1F255C !important; border-color: {"#7F96E6" if dark else "#1F255C"} !important; color: #FFFFFF !important;
  box-shadow: 0 0 20px {title["glow"]}; }}
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-primary"]:hover:not(:disabled) {{ background-color: #2B3378 !important; }}
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-secondary"],
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-secondary"]:hover:not(:disabled) {{
  background-color: {title["sub_bg"]} !important; border-color: {title["sub_border"]} !important; color: {title["sub_text"]} !important; }}
.st-key-title_screen .st-key-title_menu [data-testid="stBaseButton-secondary"]:hover:not(:disabled) {{ background-color: {title["sub_hover"]} !important; }}
.st-key-title_menu button:focus-visible {{ outline: 2px solid {title["focus"]} !important; outline-offset: 2px; }}
/* 새 면접 창 '준비 중' 직군 안내: 기본 안내 상자(네이비) 대신 연한 아이스 블루 단색 (다크는 같은 계열의 어두운 단색) */
.st-key-job_notice [data-testid="stAlertContainer"] {{ background: {"#16243A" if dark else "#F2F8FE"} !important;
  border: 1px solid {"#24385A" if dark else "#DCEAF7"}; }}
.st-key-job_notice [data-testid="stAlertContainer"] p {{ color: {title["text"]} !important; }}
/* 새 면접 ↔ 이어하기 전환 · 면접관 타입 고르기: 원티드 몽타주 Segmented Control (medium · 높이 40).
   트랙 fill.normal(coolNeutral 50 의 8% · 다크 22%), 고른 칸 background.elevated + 그림자 small, 글자 label.normal 600,
   안 고른 칸 label.alternative 500. 트랙 radius 12 · 칸 radius 8 · 안쪽 여백 4 */
:is(.st-key-mode_switch, .st-key-persona_switch) [data-testid="stButtonGroup"] {{ width: 100%; }}
:is(.st-key-mode_switch, .st-key-persona_switch) [data-testid="stButtonGroup"] > div {{
  display: flex !important; width: 100%; gap: 4px; padding: 4px; border-radius: 12px; position: relative;
  background: {"rgba(112, 115, 124, 0.22)" if dark else "rgba(112, 115, 124, 0.08)"}; }}
/* 고른 칸 표시는 버튼 바탕이 아니라 트랙 위 '알약' 하나가 옆으로 미끄러진다 (두 칸 · 칸 너비 = 트랙 안쪽 절반 - 간격 반) */
:is(.st-key-mode_switch, .st-key-persona_switch) [data-testid="stButtonGroup"] > div::before {{
  content: ""; position: absolute; top: 4px; bottom: 4px; left: 4px; width: calc(50% - 6px); border-radius: 8px;
  background: {"#37383C" if dark else "#FFFFFF"};
  box-shadow: 0 1px 2px rgba(23, 23, 23, 0.06), 0 0 1px rgba(23, 23, 23, 0.08);
  transition: transform 280ms cubic-bezier(0.2, 0, 0, 1); }}
:is(.st-key-mode_switch, .st-key-persona_switch) [data-testid="stButtonGroup"] > div:has(> :last-child[aria-checked="true"], > :last-child [aria-checked="true"])::before {{
  transform: translateX(calc(100% + 4px)); }}
:is(.st-key-mode_switch, .st-key-persona_switch) button {{ position: relative; z-index: 1; flex: 1 1 0 !important; min-height: 40px; border: none !important;
  border-radius: 8px !important; background: transparent !important; box-shadow: none !important;
  color: {"#AEB0B6" if dark else "#70737C"} !important;
  transition: color 200ms ease-out, transform 120ms ease-out; }}
:is(.st-key-mode_switch, .st-key-persona_switch) button p {{ font-weight: 500; transition: font-weight 200ms ease-out; }}
:is(.st-key-mode_switch, .st-key-persona_switch) button:hover:not([aria-checked="true"]) {{ color: {"#F7F7F8" if dark else "#171719"} !important; }}
:is(.st-key-mode_switch, .st-key-persona_switch) button:active {{ transform: scale(0.98); }}  /* 누르는 순간 살짝 눌리는 느낌 */
:is(.st-key-mode_switch, .st-key-persona_switch) button[aria-checked="true"] {{ color: {"#F7F7F8" if dark else "#171719"} !important; }}
:is(.st-key-mode_switch, .st-key-persona_switch) button[aria-checked="true"] p {{ font-weight: 600; }}
/* 면접관 타입 옆 태그 (PERSONA_TAGS): 누르는 기능 없는 정보 태그 — 양 끝 원형 알약 · 고른 칸이어도 굵기 그대로 · 클릭은 버튼으로 넘긴다 */
.st-key-persona_switch button :is(.stMarkdownBadge, [data-testid="stMarkdownBadge"]) {{
  border-radius: 999px !important; padding: 2px 8px !important; margin: 0 !important; font-size: 12px !important; font-weight: 500 !important;
  line-height: 1.4; pointer-events: none; user-select: none; }}
/* 이름 + 태그: 칸 안에 들어가면 한 줄 · 가운데, 안 들어가면 태그만 둘째 줄 가운데로 (정한 너비 없이 실제 글 길이로).
   태그는 줄을 나누지 않고, 이름은 그 자체로도 칸보다 길 때만 띄어쓰기에서 나눈다. 버튼 높이는 줄 수에 따라 늘었다 줄었다 (최소 40) */
.st-key-persona_switch button {{ height: auto !important; justify-content: center !important; }}
.st-key-persona_switch button > div, .st-key-persona_switch button > div > span,
.st-key-persona_switch button [data-testid="stMarkdownContainer"] {{ width: 100%; min-width: 0; }}
.st-key-persona_switch button p {{ display: flex !important; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 2px 4px; white-space: normal !important; word-break: keep-all; text-align: center; margin: 0 !important; }}
.st-key-persona_switch button .stMarkdownBadge {{ white-space: nowrap; flex-shrink: 0; }}
:is(.st-key-mode_switch, .st-key-persona_switch) button:focus-visible {{ outline: 2px solid {title["focus"]} !important; outline-offset: 1px; }}
@media (prefers-reduced-motion: reduce) {{
  :is(.st-key-mode_switch, .st-key-persona_switch) [data-testid="stButtonGroup"] > div::before, :is(.st-key-mode_switch, .st-key-persona_switch) button,
  :is(.st-key-mode_switch, .st-key-persona_switch) button p {{ transition: none; }}
  :is(.st-key-mode_switch, .st-key-persona_switch) button:active {{ transform: none; }} }}
/* 새 면접 · 이어하기 창 위의 작은 로고 띠 (타이틀 판과 같은 색 계열) */
.st-key-logo_bar {{ background: {title["bar"]}; border: 1px solid {title["border"]}; border-radius: 12px; padding: 10px 16px; align-items: center;
  position: relative; transition: border-color 150ms ease-out; }}
/* 띠 전체를 누르면 홈: 투명 버튼을 띠 위에 꽉 채워 겹친다 (키보드 Tab 으로도 갈 수 있고, 포커스면 테두리 표시) */
.st-key-logo_bar .st-key-logo_home {{ position: absolute !important; inset: 0; margin: 0 !important; z-index: 2; }}
.st-key-logo_bar .st-key-logo_home, .st-key-logo_bar .st-key-logo_home div,
.st-key-logo_bar .st-key-logo_home button {{ width: 100% !important; height: 100% !important; max-width: none !important; }}
.st-key-logo_bar .st-key-logo_home button {{ opacity: 0; cursor: pointer; border-radius: 12px; }}
.st-key-logo_bar:hover {{ border-color: {"#7F96E6" if dark else "#B9C6F2"}; }}
.st-key-logo_bar:has(button:focus-visible) {{ outline: 2px solid {title["focus"]}; outline-offset: 2px; }}
.st-key-logo_bar img {{ display: block; margin: 0 auto; width: 200px !important; max-width: 100%; height: auto; }}
/* 창 머리: 제목과 '타이틀로' 를 한 줄에, 아래는 구분선 */
.st-key-start_window > [data-testid="stHorizontalBlock"]:first-child {{ border-bottom: 1px solid var(--st-border-color, rgba(128,128,128,.25)); padding-bottom: 8px; }}
/* 면접관 소개: 머리줄(persona_head)은 카드 밖, 칸마다 회색 카드(persona_card_줄칸) 2열 (회색 · config.toml grayBackgroundColor 와 같은 값) */
.st-key-persona_head {{ gap: 2px; }}
.st-key-persona_cards {{ gap: 12px; }}
.st-key-persona_cards [data-testid="stHorizontalBlock"] {{ align-items: stretch; }}  /* 같은 줄 두 카드 높이 맞춤 */
.st-key-persona_cards [data-testid="stColumn"] > div {{ height: 100%; }}
[class*="st-key-persona_card_"] {{ height: 100%; background: {"#292A2D" if dark else "#F4F4F5"}; border-radius: 12px; padding: 14px 18px 18px; }}
/* 카드 안: 소제목은 작게, 항목은 본문보다 한 단계 작게 (config.toml grayTextColor) */
[class*="st-key-persona_card_"] p {{ font-size: 0.8rem; font-weight: 600; color: {"#C2C4C8" if dark else "#46474C"}; margin: 0 0 4px; }}
[class*="st-key-persona_card_"] ul {{ margin: 0; padding-left: 1.1rem; }}
[class*="st-key-persona_card_"] li {{ font-size: 0.875rem; line-height: 1.55; margin: 0 0 2px; word-break: keep-all; }}
[class*="st-key-persona_card_"] li:last-child {{ margin-bottom: 0; }}
/* Streamlit 은 마크다운 칸 아래에 -16px 를 줘서 마지막 글이 카드 바닥 여백을 파고든다 → 0 */
[class*="st-key-persona_card_"] [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
/* 면접 화면 내 답 말풍선: 오른쪽 여백을 16px → 32px (글이 오른쪽 끝에 붙어 보이지 않게) */
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {{ padding-right: 32px !important; }}
/* 암기 탭 질문 카드: 좁은 화면에서도 < 질문 > 을 한 줄로 (Streamlit 은 640px 아래에서 칸을 세로로 쌓는다) */
/* < 윗줄 > 은 카드 양끝이 아니라 윗줄 글 바로 옆에 30px 띄워 가운데로 모은다 */
.st-key-memo_qcard [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; justify-content: center; gap: 30px !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:nth-child(2) {{ flex: 0 1 auto !important; width: auto !important; }}
.st-key-memo_qcard [data-testid="stColumn"] {{ min-width: 0 !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:first-child, .st-key-memo_qcard [data-testid="stColumn"]:last-child {{
  flex: 0 0 44px !important; width: 44px !important; }}
.st-key-memo_qcard [data-testid="stColumn"]:nth-child(2) [data-testid="stCaptionContainer"] {{ text-align: center; }}
.st-key-memo_qcard h4 {{ text-align: center; word-break: keep-all; }}
.st-key-memo_qcard [data-testid="stMarkdownContainer"] p:has(> .stMarkdownBadge) {{ text-align: center; }}  /* 공통 · 분야 질문 태그 */  /* 한국어는 어절 단위로 줄바꿈 */
</style>"""


st.html(hover_css())

# 남는 도움말 닫기: 버튼을 누르면 Streamlit 이 버튼을 새로 그리는데, 그때 열려 있던 도움말(help)은
# '마우스가 떠났다' 신호를 받지 못해 화면에 남는다 (암기 탭 < > 에서 재현). 마우스가 도움말 버튼에도,
# 도움말 위에도 없는데 보이는 도움말은 숨긴다. 고정 문장만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
# (스크립트 글에 태그 모양 글자가 있으면 Streamlit 정리기가 스크립트를 통째로 지우므로 쓰지 않는다)
TOOLTIP_GUARD_JS = """<script>
(() => {
  if (window.__tooltipGuard) return;
  window.__tooltipGuard = true;
  let x = -1, y = -1, timer = 0;
  // 도움말 버튼 칸은 aria-describedby 로 자기 도움말 id 를 가리킨다: 마우스가 그 버튼이나 그 도움말 위일 때만 보인다
  const check = () => {
    const over = x >= 0 ? document.elementFromPoint(x, y) : null;
    const target = over && over.closest('[data-testid="stTooltipHoverTarget"]');
    const hoveredTip = over && over.closest('[role="tooltip"]');
    const mine = target ? target.getAttribute("aria-describedby") : null;
    document.querySelectorAll('[role="tooltip"]').forEach((tip) => {
      tip.style.display = (tip.id && tip.id === mine) || tip === hoveredTip ? "" : "none";
    });
  };
  const later = (ms) => { clearTimeout(timer); timer = setTimeout(check, ms); };
  document.addEventListener("pointermove", (e) => { x = e.clientX; y = e.clientY; later(250); }, true);
  document.addEventListener("click", () => later(700), true);
  document.addEventListener("scroll", () => later(250), true);
})();
</script>"""
st.html(TOOLTIP_GUARD_JS, unsafe_allow_javascript=True)



def scroll_to_anchor(anchor: str):
    """화면을 제목(anchor) 위치로 내린다. 스크립트는 고정 문장이고 anchor 이름(코드에 적힌 글자)과 실행 번호만 넣는다.
    탭이 막 바뀐 뒤라 제목이 그려질 때까지 잠깐 기다렸다가 내린다."""
    state["scroll_seq"] = state.get("scroll_seq", 0) + 1
    st.html(
        f"""<script>/* {int(state["scroll_seq"])} */
(() => {{
  let tries = 0;
  const go = () => {{
    const el = document.getElementById({anchor!r});
    if (el) {{ el.scrollIntoView({{ block: "start", behavior: "instant" }}); return; }}
    if (++tries != 20) setTimeout(go, 100);
  }};
  setTimeout(go, 150);
}})();
</script>""",
        unsafe_allow_javascript=True,
    )


def scroll_to_top():
    """페이지 맨 위로 (Streamlit 에 스크롤 기능이 없어서 짧은 스크립트로).
    스크립트는 고정 문장이고 숫자(실행 번호)만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
    실행 번호를 넣어야 같은 자리에 다시 그려져도 스크립트가 새로 돈다."""
    state["scroll_seq"] = state.get("scroll_seq", 0) + 1
    st.html(
        f"""<script>/* {int(state["scroll_seq"])} */
for (const el of [document.scrollingElement, ...document.querySelectorAll('[data-testid="stAppScrollToBottomContainer"], [data-testid="stMain"], [data-testid="stAppViewContainer"]')]) {{
  if (el) el.scrollTo({{ top: 0, behavior: "instant" }});
}}
</script>""",
        unsafe_allow_javascript=True,
    )
DEFAULT_TIMEZONE = "Asia/Seoul"  # 브라우저 시간대를 모를 때
DEV_MOCK = os.getenv("DEV_MOCK", "").strip() == "1"  # 개발용 모의 데이터 버튼 (.env 에만, 배포 Secrets 에는 넣지 않는다)


# 리포트 태그: 처음부터 있는 태그 (기준은 비워 두고 사용자가 채운다). 태그 순서 = 상태창 목록 순서
DEFAULT_TAGS = [{"name": "1지망", "rule": ""}, {"name": "2지망", "rule": ""}]


def default_job() -> str:
    """처음 고를 직군: 면접관 페르소나가 있는 첫 직군 (지금은 디자인)."""
    return next((j for j in coach.JOBS if PERSONAS[j]), coach.JOBS[0])


def reset(job: str | None = None, field: str | None = None):
    """시작 화면(한 화면)으로. job 이 없으면 기본 직군이 골라진 채로 연다 (직군 고르기 화면을 따로 두지 않는다).
    불러온 리포트 목록(reports) · 그룹(report_groups · report_group_of) · 태그(report_tags · report_tag_of)는
    지우지 않는다 (상태창에서 회사를 바꿔 가며 쓰고, 정해 둔 태그 기준을 다시 쓰도록)."""
    kept = {key: st.session_state.get(key, default) for key, default in
            (("reports", {}), ("report_groups", []), ("report_group_of", {}),
             ("report_tags", None), ("report_tag_of", {}), ("splash_done", False))}
    if kept["report_tags"] is None:
        kept["report_tags"] = [dict(t) for t in DEFAULT_TAGS]
    st.session_state.clear()
    st.session_state.update(kept)
    st.session_state.stage = "start"
    st.session_state.job = job or default_job()
    st.session_state.field = field if field in FIELDS else coach.DEFAULT_FIELD


if "stage" not in st.session_state:
    reset()

state = st.session_state
if not (state.stage == "start" and state.get("start_mode") == "resume"):
    state.pop("uploader_ids", None)  # 올리기 칸이 안 그려지면 칸이 비워지므로, 직전 목록도 잊는다

# 아이콘 캐릭터 (원작 그래픽 대신 이모지)
AVATARS = {"assistant": ":material/support_agent:", "user": ":material/person:"}


def call_ai(spinner_text: str, instructions: str, user_input: str, schema: dict, name: str, store) -> bool:
    """AI를 한 번 부르고, 결과를 받자마자 store(결과) 로 저장한다. 실패하면 한국어 한 줄 에러.
    Streamlit 은 응답을 기다리는 동안 다른 버튼을 누르면 실행을 멈추고 다시 시작한다.
    저장을 화면 그리기 뒤로 미루면 받은 결과를 버리고 다시 호출하게 돼서, spinner 안에서 바로 저장한다."""
    try:
        with st.spinner(spinner_text):
            store(ask_json(instructions, user_input, schema, name))
    except LLMError as e:
        st.error(str(e))
        return False
    return True


def question_message(index: int) -> dict:
    question = state.questions[index]
    field = question.get("field", coach.DEFAULT_FIELD)
    tag = f" :material/explore: **{field} 질문**" if field != coach.DEFAULT_FIELD else ""
    text = f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.**{tag} {question['question']}"
    return {"role": "assistant", "content": text, "q": index, "kind": "question"}


# 상태창 이동은 두 개만: 홈(분야 · 직군을 다시 고름) · 처음부터 다시(같은 모드로 새 면접).
# '분야 다시 고르기' · '직군 다시 고르기' 는 홈이 고르던 값을 미리 골라 두는 것으로 대신한다
# (ui-ux-pro-max: Forms · Redundant Entry — 이전에 고른 값을 다시 입력하게 하지 않기).
NAV_BUTTONS = [
    (":material/home: 홈으로 돌아가기", "home", "타이틀 화면으로 가요. 새 면접 · 이어하기를 다시 골라요."),
    (":material/restart_alt: 처음부터 다시", "restart", "같은 분야 · 직군 모드로 새 면접을 시작해요."),
]


def leave(target: str):
    """상태창 이동. home: 분야 · 직군 고르기 (고르던 값 유지) · restart: 같은 모드로 새 면접."""
    job, field = state.get("job"), state.get("field")
    if target in ("restart", "back"):  # back: 위쪽 '뒤로' (면접 중 · 끝난 뒤 → 같은 직군 새 면접 창)
        reset(job, field)
        state.start_mode = "new"
        return
    reset()  # 홈: 타이틀 화면 (기본 직군)


def job_reports() -> dict:
    """불러온 리포트 중 지금 직군 것만 (올린 순서대로)."""
    return {fid: r for fid, r in state.get("reports", {}).items() if r["profile"]["job"] == state.get("job")}


MAX_GROUP_NAME_CHARS = 20
NO_GROUP = "그룹 없음"


def remove_report(fid: str):
    """불러온 목록에서 리포트를 뺀다 (내 컴퓨터의 파일은 그대로). 이어 하던 리포트면 시작 화면 칸도 비운다."""
    state.reports.pop(fid, None)
    state.setdefault("report_group_of", {}).pop(fid, None)
    state.setdefault("report_tag_of", {}).pop(fid, None)
    state.setdefault("report_errors", {}).pop(fid, None)
    if state.get("active_report") == fid:
        state.active_report = None
        if state.stage in ("start", "briefing"):
            state.previous = None  # 면접 중이면 '지난 면접과 비교' 는 그대로 둔다


def set_report_group(fid: str):
    """리포트 관리의 그룹 고르기 칸이 바뀌면 그 값으로 그룹을 바꾼다."""
    group = state[f"group_of_{fid}"]
    if group == NO_GROUP:
        state.report_group_of.pop(fid, None)
    else:
        state.report_group_of[fid] = group


def add_group():
    name = state.get("new_group", "").strip()
    if not name:
        state.group_msg = "그룹 이름을 적어 주세요."
    elif name == NO_GROUP or name in state.report_groups:
        state.group_msg = f"'{name}' 은(는) 이미 있는 이름이에요. 다른 이름을 적어 주세요."
    else:
        state.report_groups.append(name)
        state.new_group = ""
        state.group_msg = None


def remove_group(name: str):
    """그룹만 지운다. 속한 리포트는 '그룹 없음' 으로 옮긴다."""
    state.report_groups.remove(name)
    for fid in [f for f, g in state.report_group_of.items() if g == name]:
        del state.report_group_of[fid]


MAX_TAG_NAME_CHARS = 10
MAX_TAG_RULE_CHARS = 60
NO_TAG = "태그 없음"

# 붙여넣기 글자 수 맞춤: Streamlit 은 max_chars 보다 긴 글을 붙여 넣으면 통째로 무시한다 (아무것도 안 들어가고 안내도 없음).
# 그래서 넘치면 상한까지만 넣고 화면 아래에 한 줄로 알린다. 칸은 key 앞부분으로 찾는다 (긴 이름부터 맞춰 본다).
# 스크립트에는 고정 문장과 상한 숫자만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
# (스크립트 글에 태그 모양 글자가 있으면 Streamlit 정리기가 스크립트를 통째로 지우므로 부등호 '작다' 쪽은 쓰지 않는다)
PASTE_LIMITS = {
    "f_experience": coach.MAX_EXPERIENCE_CHARS,
    "retry_answer_": coach.MAX_ANSWER_CHARS,
    "memo_try_": coach.MAX_ANSWER_CHARS,
    "memo_draft_": coach.MAX_ANSWER_CHARS,
    "last_question_input": coach.MAX_LAST_QUESTION_CHARS,
    "pre_memo_": coach.MAX_MEMO_CHARS,
    "new_group": MAX_GROUP_NAME_CHARS,
    "new_tag_rule": MAX_TAG_RULE_CHARS,
    "tag_rule_": MAX_TAG_RULE_CHARS,
    "new_tag": MAX_TAG_NAME_CHARS,
}
PASTE_GUARD_JS = """<script>
(() => {
  window.__pasteLimits = %s;
  window.__chatLimit = %d;
  if (window.__pasteGuard) return;
  window.__pasteGuard = true;
  const limitOf = (el) => {
    if (el.closest('[data-testid="stChatInput"]')) return window.__chatLimit;
    const box = el.closest('[class*="st-key-"]');
    if (!box) return 0;
    const key = [...box.classList].find((c) => c.startsWith("st-key-")).slice(7);
    const prefix = Object.keys(window.__pasteLimits).sort((a, b) => b.length - a.length).find((p) => key.startsWith(p));
    return prefix ? window.__pasteLimits[prefix] : 0;
  };
  let timer = 0;
  const note = (text) => {
    let el = document.getElementById("paste-note");
    if (!el) {
      el = document.createElement("div");
      el.id = "paste-note";
      el.setAttribute("role", "status");
      el.style.cssText = "position:fixed;left:50%%;bottom:24px;transform:translateX(-50%%);z-index:999999;max-width:calc(100vw - 32px);padding:10px 16px;border-radius:10px;background:#171719;color:#F7F7F8;font-size:14px;line-height:1.5;box-shadow:0 4px 16px rgba(0,0,0,.18);word-break:keep-all;";
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.style.display = "block";
    clearTimeout(timer);
    timer = setTimeout(() => { el.style.display = "none"; }, 6000);
  };
  document.addEventListener("paste", (e) => {
    const el = e.target;
    if (!el || !el.matches || !el.matches("input, textarea")) return;
    const limit = limitOf(el);
    if (!limit) return;
    const text = (e.clipboardData || window.clipboardData).getData("text");
    const room = limit - (el.value.length - (el.selectionEnd - el.selectionStart));
    if (room >= text.length) return;
    e.preventDefault();
    let part = room > 0 ? text.slice(0, room) : "";
    const last = part.charCodeAt(part.length - 1);
    if (last >= 0xD800 && 0xDBFF >= last) part = part.slice(0, -1);  // 이모지 반쪽은 넣지 않는다
    if (part) document.execCommand("insertText", false, part);
    note(limit.toLocaleString() + "자까지만 넣었어요. 붙여 넣은 글 중 뒷부분 " + (text.length - part.length).toLocaleString() + "자는 빠졌어요.");
  }, true);
})();
</script>"""
st.html(PASTE_GUARD_JS % (json.dumps(PASTE_LIMITS), coach.MAX_ANSWER_CHARS), unsafe_allow_javascript=True)

# 시작 화면 지원 정보: 네 칸(이름 · 회사 이름 · 회사 설명 · 내 경험)이 다 찰 때까지 시작 버튼을 비활성화한다.
# 폼(st.form)은 제출 전 값을 서버로 보내지 않아서 서버가 알 수 없으므로, 브라우저에서 칸을 보고 버튼만 막는다.
# 빈칸 · 글자 수 확인은 서버(started)에서 그대로 한다 (칸에서 Enter 로 제출하는 경우까지).
# 스크립트에는 고정 문장과 칸 key 만 넣는다 — 사용자 글 · AI 출력 · 키는 넣지 않는다.
START_GUARD_JS = """<script>
(() => {
  if (window.__startGuard) return;
  window.__startGuard = true;
  const keys = ["f_name", "f_company", "f_company_desc", "f_experience"];
  const fieldOf = (k) => document.querySelector(".st-key-" + k + " input, .st-key-" + k + " textarea");
  const check = () => {
    const first = fieldOf(keys[0]);
    const form = first && first.closest('[data-testid="stForm"]');
    const btn = form && form.querySelector('[data-testid="stFormSubmitButton"] button');
    if (!btn) return;
    const filled = keys.every((k) => { const el = fieldOf(k); return el && el.value.trim().length > 0; });
    if (btn.disabled === filled) {
      btn.disabled = !filled;
      btn.setAttribute("aria-disabled", String(!filled));
      btn.title = filled ? "" : "필수 항목(이름 · 회사 이름 · 회사 설명 · 내 경험)을 모두 채우면 시작할 수 있어요.";
    }
  };
  document.addEventListener("input", check, true);
  setInterval(check, 300);
})();
</script>"""
st.html(START_GUARD_JS, unsafe_allow_javascript=True)


def tag_rank(fid: str) -> int:
    """상태창에서 태그 순서대로 (1지망 → 2지망 → … → 태그 없음)."""
    names = [t["name"] for t in state.report_tags]
    tag = state.report_tag_of.get(fid)
    return names.index(tag) if tag in names else len(names)


def set_report_tag(fid: str):
    tag = state[f"tag_of_{fid}"]
    if tag == NO_TAG:
        state.report_tag_of.pop(fid, None)
    else:
        state.report_tag_of[fid] = tag


def set_tag_rule(i: int):
    state.report_tags[i]["rule"] = state[f"tag_rule_{i}"].strip()


def add_tag():
    name = state.get("new_tag", "").strip()
    if not name:
        state.tag_msg = "태그 이름을 적어 주세요."
    elif name == NO_TAG or name in [t["name"] for t in state.report_tags]:
        state.tag_msg = f"'{name}' 은(는) 이미 있는 태그예요. 다른 이름을 적어 주세요."
    else:
        state.report_tags.append({"name": name, "rule": state.get("new_tag_rule", "").strip()})
        state.new_tag, state.new_tag_rule = "", ""
        state.tag_msg = None


def remove_tag(i: int):
    """태그만 지운다. 그 태그가 붙은 리포트는 '태그 없음' 으로."""
    name = state.report_tags.pop(i)["name"]
    for fid in [f for f, t in state.report_tag_of.items() if t == name]:
        del state.report_tag_of[fid]
    for key in [k for k in state if str(k).startswith("tag_rule_")]:
        del state[key]  # 번호가 밀리므로 기준 칸 값을 새로 채운다


def activate_report(fid: str):
    """불러온 리포트 하나를 '이어 할 회차' 로 정하고 시작 화면 칸을 채운다."""
    report = state.reports[fid]
    state.active_report = fid
    state.previous = report
    state.start_mode = "resume"
    state.job = report["profile"]["job"]  # 이어하기 창은 직군을 고르지 않고 리포트의 직군으로 연다
    state.field = report["profile"]["field"]  # 이어 하는 리포트의 분야로 맞춘다 (시작 화면에서 바꿀 수 있다)
    state.start_field = state.field
    for field in ("name", "company", "company_desc", "experience"):
        state[f"f_{field}"] = report["profile"][field]
    # 경험 칸 글자 수 상한에 맞춘다 (상한보다 긴 값을 넣으면 칸이 에러를 낸다)
    state.f_experience = state.f_experience[: coach.MAX_EXPERIENCE_CHARS]


def resume_without_interview(previous: dict, name, job, company, company_desc, experience, notice: str | None = None):
    """면접을 다시 하지 않고 리포트의 결과로 같은 회차를 이어 간다 (면접이 끝난 상태로 시작).
    시작 화면에서 부르므로 시작 화면 코드보다 위에 둔다. 개발용 모의 데이터도 이 길로 연다."""
    try:
        questions = coach.match_questions(coach.load_questions(), job, previous["questions"])
    except (OSError, ValueError, KeyError):
        st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
        return
    if questions is None:
        st.warning("지난 질문 중 질문 은행에 없는 질문이 있어서 이어 할 수 없어요. 체크를 풀고 새 면접으로 시작해 주세요.")
        return
    session = coach.rebuild_session(previous["session"], questions)
    state.profile = {
        "name": name, "field": state.get("field", coach.DEFAULT_FIELD), "job": job,
        "company": company, "company_desc": company_desc, "experience": experience,
        "persona_type": state.get("persona_type"),  # 면접관 타입 (리포트에는 남기지 않아 리포트로 이어 하면 기본 타입)
    }
    state.questions = questions
    state.round = previous["round"]   # 같은 회차를 이어 간다
    state.previous = None             # 같은 회차라 '지난 면접과 비교' 는 하지 않는다
    restore_precheck(previous["precheck"])
    state.q_index = coach.TOTAL_QUESTIONS
    state.follow_ups = 0
    for key in ("messages", "evaluation", "retries", "retry_history", "retry_counts", "last_suggest", "last_question", "understanding"):
        state[key] = session[key]
    state.highlights, state.strategies = {}, {}
    state.memo_edits, state.memo_reviews = {}, {}  # 검토 내역은 retry_history 의 몇 번째인지라 새 기록과 맞지 않는다
    # 실마리: 리포트에 저장돼 있으면 그 회차 · 목록에서 이어 간다 (없으면 1회차 · 새로 찾기)
    state.pop("clue_set", None)
    if session["clue_set"] is not None:
        state.clue_set = session["clue_set"]
    state.clue_round = session["clue_round"]
    state.verdict_open = False
    state.same_questions = True
    state.open_eval = True            # 평가 탭부터 보여 준다
    state.notice = notice or f"{previous['round']}회차 결과를 불러왔어요. 면접 없이 평가 · 재도전 · 암기 · 리포트를 이어서 할 수 있어요."
    state.stage = "done"
    st.rerun()


def restore_precheck(saved: dict):
    """지난 회차 리포트의 체크 · 메모를 지금 체크리스트에 채운다 (항목 글자로 맞춘다).
    시작 화면에서 부르므로 시작 화면 코드보다 위에 둔다."""
    try:
        items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        return
    for i, item in enumerate(items):
        if item["item"] in saved:
            value = saved[item["item"]]
            state[f"pre_found_{i}"] = value["found"]
            state[f"pre_missing_{i}"] = value["missing"]
            state[f"pre_memo_{i}"] = value["memo"][: coach.MAX_MEMO_CHARS]  # 메모 칸 글자 수 상한에 맞춤


# ── 사이드바 상태창 ──────────────────────────────────────────
with st.sidebar:
    st.header("상태창")
    if state.get("job"):
        st.markdown(
            f"**{state.get('field', coach.DEFAULT_FIELD)} · {state.job} 직군 모드**"
            + (f" · {state.round}회차" if state.get("round") else "")
        )
    if state.stage == "pick":
        st.caption("직군을 고르면 시작할 수 있어요.")
    elif state.stage == "start" and state.get("start_mode") not in ("new", "resume"):
        st.caption("새 면접을 시작하거나 이전 면접을 이어 해 주세요.")
    elif state.stage == "start":
        st.caption("면접을 시작하면 진행 상황이 보여요.")
    elif state.stage == "briefing":
        st.caption("브리핑을 확인하고 면접을 시작해 주세요.")
    else:
        answered = state.q_index
        current = min(answered + 1, coach.TOTAL_QUESTIONS)
        st.progress(answered / coach.TOTAL_QUESTIONS, text=f"질문 {current}/{coach.TOTAL_QUESTIONS}")
        st.metric("면접관이 본 이해도", "-" if state.understanding is None else f"{state.understanding}/100")
        if state.get("evaluation"):
            ev = state.evaluation
            totals = coach.total_scores(ev, state.get("retries", {}))
            st.metric(
                "종합 점수", f"{totals['latest']}/{coach.TOTAL_MAX}",
                delta=totals["diff"] or None, help="재도전한 질문은 재도전 점수로 바꿔 넣은 합이에요.",
            )
            st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    # 불러온 리포트: 누르면 그 회사로 바꾼다. 면접 중이면 기록이 사라지니 한 번 더 확인한다.
    loaded = job_reports() if state.stage != "pick" else {}
    if loaded:
        st.divider()
        st.markdown("**:material/folder_open: 불러온 리포트**")
        groups = state.setdefault("report_groups", [])
        group_of = state.setdefault("report_group_of", {})
        tags = state.setdefault("report_tags", [dict(t) for t in DEFAULT_TAGS])
        tag_of = state.setdefault("report_tag_of", {})
        tag_rules = {t["name"]: t["rule"] for t in tags}
        loaded = dict(sorted(loaded.items(), key=lambda item: tag_rank(item[0])))  # 1지망 → 2지망 → … 순서

        def report_label(fid: str) -> str:
            report = loaded[fid]
            return f"{report['profile']['company']} · {report['round']}회차 ({report['date'][5:]})"

        def report_button(fid: str):
            active = state.get("active_report") == fid
            tag = tag_of.get(fid) if tag_of.get(fid) in tag_rules else None
            label = (":material/check: " if active else "") + (f"`{tag}` " if tag else "") + report_label(fid)
            tip = (f"{tag} 기준: {tag_rules[tag]}" if tag_rules[tag] else f"{tag} · 기준은 '리포트 관리' 에서 적을 수 있어요") if tag else None
            if st.button(label, key=f"report_{fid}", width="stretch", type="primary" if active else "secondary", help=tip):
                if state.stage in ("start", "briefing"):
                    activate_report(fid)
                    state.stage = "start"
                    st.rerun()
                elif not active:
                    state.switch_pending = fid
                    st.rerun()

        # 그룹 없는 리포트 먼저, 그다음 그룹마다 접기 칸 (이어 하는 리포트가 든 그룹은 펼쳐 둔다)
        for fid in loaded:
            if group_of.get(fid) not in groups:
                report_button(fid)
        for group in groups:
            members = [fid for fid in loaded if group_of.get(fid) == group]
            with st.expander(f":material/folder: {group} ({len(members)})",
                             expanded=state.get("active_report") in members):
                if not members:
                    st.caption("비어 있어요. '리포트 관리' 에서 리포트를 넣어 주세요.")
                for fid in members:
                    report_button(fid)

        with st.popover(":material/tune: 리포트 관리", width="stretch"):
            st.markdown("**그룹 만들기**")
            st.text_input("새 그룹 이름", key="new_group", max_chars=MAX_GROUP_NAME_CHARS,
                          placeholder="예: 1지망 · 핀테크")
            st.button(":material/create_new_folder: 그룹 만들기", on_click=add_group, width="stretch")
            if state.get("group_msg"):
                st.info(state.group_msg)
            st.markdown("**태그 설정**")
            st.caption("1지망 · 2지망처럼 기준을 한 번 적어 두면, 리포트마다 태그만 골라 바로 다시 쓸 수 있어요. "
                       "상태창 목록은 태그 순서대로 보여요.")
            for i, tag in enumerate(tags):
                state.setdefault(f"tag_rule_{i}", tag["rule"])
                rule_col, del_col = st.columns([4, 1], vertical_alignment="bottom")
                rule_col.text_input(f"`{tag['name']}` 기준", key=f"tag_rule_{i}", max_chars=MAX_TAG_RULE_CHARS,
                                    placeholder="예: 연봉 4천 이상 · 핀테크 · 서울", on_change=set_tag_rule, args=(i,))
                del_col.button(":material/delete:", key=f"del_tag_{i}", help=f"'{tag['name']}' 태그 지우기 "
                               "(붙어 있던 리포트는 '태그 없음' 으로)", on_click=remove_tag, args=(i,))
            name_col, new_rule_col = st.columns([2, 3])
            name_col.text_input("새 태그", key="new_tag", max_chars=MAX_TAG_NAME_CHARS, placeholder="예: 3지망")
            new_rule_col.text_input("기준", key="new_tag_rule", max_chars=MAX_TAG_RULE_CHARS, placeholder="예: 경험 쌓기용")
            st.button(":material/new_label: 태그 추가", on_click=add_tag, width="stretch")
            if state.get("tag_msg"):
                st.info(state.tag_msg)
            st.markdown("**리포트마다 태그 · 그룹 · 삭제**")
            options = [NO_GROUP, *groups]
            tag_options = [NO_TAG, *tag_rules]
            for fid in loaded:
                key, tag_key = f"group_of_{fid}", f"tag_of_{fid}"
                state[key] = group_of.get(fid) if group_of.get(fid) in groups else NO_GROUP  # 지운 그룹은 '그룹 없음'
                state[tag_key] = tag_of.get(fid) if tag_of.get(fid) in tag_rules else NO_TAG  # 지운 태그는 '태그 없음'
                st.markdown(f"**{report_label(fid)}**")
                tag_col, group_col, del_col = st.columns([2, 2, 1], vertical_alignment="bottom")
                tag_col.selectbox("태그", tag_options, key=tag_key, on_change=set_report_tag, args=(fid,))
                group_col.selectbox("그룹", options, key=key, on_change=set_report_group, args=(fid,))
                if del_col.button(":material/delete:", key=f"del_report_{fid}", help="목록에서 빼기"):
                    state.delete_pending = fid
                    st.rerun()
            if groups:
                st.markdown("**그룹 지우기**")
                st.caption("그룹만 지워요. 속한 리포트는 '그룹 없음' 으로 옮겨져요.")
                for group in groups:
                    st.button(f":material/folder_delete: '{group}' 그룹 지우기", key=f"del_group_{group}",
                              on_click=remove_group, args=(group,), width="stretch")
            st.caption(":material/info: 목록 · 그룹 · 태그는 이 화면에만 있어요. 새로고침하면 사라지니, "
                       "리포트 파일은 내 컴퓨터에 보관해 주세요.")

        doomed = state.get("delete_pending")
        if doomed in loaded:
            st.warning(f"'{report_label(doomed)}' 리포트를 목록에서 뺄까요? 내 컴퓨터의 파일은 지워지지 않아요.")
            yes_col, no_col = st.columns(2)
            if yes_col.button("빼기", type="primary", width="stretch"):
                state.setdefault("report_dismissed", set()).add(doomed)  # 올리기 칸에 남아 있어도 다시 넣지 않는다
                remove_report(doomed)
                state.delete_pending = None
                st.rerun()
            if no_col.button("취소", key="cancel_delete", width="stretch"):
                state.delete_pending = None
                st.rerun()
        pending = state.get("switch_pending")
        if pending in loaded:
            company = loaded[pending]["profile"]["company"]
            st.warning(f"'{company}' 로 바꾸면 지금 면접 기록이 사라져요. :material/description: 리포트를 받아 두었나요?")
            yes_col, no_col = st.columns(2)
            if yes_col.button("바꾸기", type="primary", width="stretch"):
                reset(state.job, state.get("field"))
                activate_report(pending)
                st.rerun()
            if no_col.button("취소", width="stretch"):
                state.switch_pending = None
                st.rerun()
        st.divider()

    # 이동 버튼. 면접 중 · 끝난 뒤에는 기록이 사라지니 한 번 더 확인한다.
    if state.stage != "pick":
        for label, target, tip in NAV_BUTTONS:
            if st.button(label, key=f"nav_{target}", width="stretch", help=tip):
                if state.stage in ("interview", "done"):
                    state.leave_pending = target
                else:
                    leave(target)
                st.rerun()


LEAVE_TEXT = {"home": "타이틀 화면으로 가면", "restart": "처음부터 다시 하면", "back": "시작 화면으로 돌아가면"}


@st.dialog("이동하기 전에 확인해 주세요")
def leave_dialog(target: str):
    """면접 중 · 끝난 뒤의 이동 확인 (상태창 버튼 · 위쪽 '뒤로' 가 같이 쓴다). 오른쪽 위 ✕ 는 머무르기."""
    st.warning(f"{LEAVE_TEXT[target]} 지금 면접 기록이 사라져요. :material/description: 리포트를 저장해 두었나요?")
    stay_col, go_col = st.columns(2)
    if stay_col.button("머무르기", key="leave_stay", width="stretch"):
        st.rerun()
    if go_col.button("이동하기", key="leave_go", type="primary", width="stretch"):
        leave(target)
        st.rerun()


if state.get("leave_pending"):
    leave_dialog(state.pop("leave_pending"))


def go_back():
    """위쪽 '뒤로': 브리핑 → 시작 화면(입력값 그대로) · 면접 중 · 끝난 뒤 → 확인 후 시작 화면. (시작 화면이 첫 화면)"""
    if state.stage == "briefing":
        for name in ("name", "company", "company_desc", "experience"):
            state[f"f_{name}"] = state.profile[name]
        state.stage = "start"
    elif state.stage in ("interview", "done"):
        state.leave_pending = "back"


# 로고: 라이트는 파랑(logo.png), 다크는 은색(logo_dark.png). 테마는 hover_css 와 같은 방법으로 안다
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO = os.path.join(_ASSETS, "logo_dark.png" if getattr(st.context.theme, "type", None) == "dark" else "logo.png")


def go_home_from_logo():
    """맨 위 로고 띠 (콜백): 홈(타이틀 화면)으로. 새 면접 · 이어하기 창에서는 적던 값을 맡겨 두고 타이틀로 (예전 '타이틀로' 버튼),
    면접 중 · 끝난 뒤에는 기록이 사라지니 상태창 홈 버튼처럼 한 번 더 묻는다."""
    if state.stage == "start" and state.get("start_mode") in ("new", "resume"):
        to_title()
    elif state.stage in ("interview", "done"):
        state.leave_pending = "home"
    else:
        leave("home")


# 맨 위: 로고 띠 (타이틀 화면 말고 모든 화면). 띠 전체가 홈 버튼 — 투명 버튼을 띠 위에 겹친다 (hover_css)
if not (state.stage in ("pick", "start") and state.get("start_mode") not in ("new", "resume")):
    with st.container(key="logo_bar"):
        st.image(LOGO)
        st.button("홈으로 돌아가기", key="logo_home", on_click=go_home_from_logo)

# 맨 위: 뒤로 (시작 화면은 첫 화면이라 없다)
if state.stage not in ("pick", "start"):
    st.button(":material/arrow_back: 뒤로", key="top_back", on_click=go_back,
              help="한 단계 앞 화면으로 가요. 면접 중이면 한 번 더 물어봐요.")


# ── 시작: 타이틀 화면 → 새 면접 창 (직군 · 지원 정보) / 이어하기 창 (리포트 불러오기 · 분야 · 지원 정보) ──
# 창의 입력 칸 key. 타이틀 화면에는 칸이 안 그려져서 Streamlit 이 값을 지우므로, 타이틀로 갈 때 따로 맡겨 둔다
WINDOW_KEYS = ("f_name", "f_company", "f_company_desc", "f_experience", "resume_skip", "previous_mode", "start_field")


# 창마다 맡겨 두는 값: 입력 칸 + 이어 하는 리포트 (새 면접 ↔ 이어하기를 오가도 각자 적던 값이 남게)
DRAFT_KEYS = (*WINDOW_KEYS, "previous", "active_report")
MODE_LABELS = {"new": ":material/play_arrow: 새 면접 시작", "resume": ":material/folder_open: 이전 면접 이어하기"}


def stash_window():
    """지금 창(새 면접 / 이어하기)의 값을 그 창 몫으로 맡겨 둔다."""
    mode = state.get("start_mode")
    if mode in ("new", "resume"):
        state.setdefault("window_drafts", {})[mode] = {k: state[k] for k in DRAFT_KEYS if k in state}


def open_window(mode: str):
    """창 열기 (타이틀 메뉴 · 창 위 전환 버튼 콜백). 맡겨 둔 값이 있으면 되돌리고, 없으면 새로
    (이어하기는 불러온 리포트가 있으면 마지막 것으로). 불러온 목록 · 그룹 · 태그는 남긴다."""
    draft = state.setdefault("window_drafts", {}).pop(mode, None)
    for key in DRAFT_KEYS:
        state.pop(key, None)
    state.start_mode = mode
    if draft:
        state.update(draft)
    elif mode == "resume" and state.get("reports"):
        activate_report(list(state.reports)[-1])


def to_title():
    """타이틀로 (맨 위 로고 띠 콜백). 적던 칸은 맡겨 두고, 불러온 리포트는 그대로 둔다."""
    stash_window()
    state.start_mode = None


def switch_window():
    """창 위 전환 버튼 (콜백): 지금 창 값을 맡겨 두고 다른 창으로."""
    stash_window()
    open_window(state.mode_switch)


if state.stage in ("pick", "start") and state.get("start_mode") not in ("new", "resume"):
    # 타이틀 화면: 게임 첫 화면처럼 로고 + 메뉴 두 개만
    with st.container(key="title_screen"):
        st.image(LOGO)  # 스플래시 · 홈이 같이 쓰는 로고 하나 (움직이지 않는다)
        with st.container(key="title_stage"):
            # 스플래시 문구: 들어올 때 한 번만 그린다 (홈 버튼으로 돌아와도 다시 나오지 않게 reset 이 splash_done 을 남긴다)
            if not state.get("splash_done"):
                state.splash_done = True
                with st.container(key="splash_text"):
                    with st.container(key="splash_head"):
                        st.markdown("질문을 파악하고, 전략을 강화하라!")
                    with st.container(key="splash_sub"):
                        st.markdown("합격을 향한 전세역전(戰勢逆轉) 취업 코칭 서비스")
            with st.container(key="title_body"):
                st.markdown("모의면접 · 질문 5개와 꼬리 질문으로 경험과 전략을 발전시켜요.")
                with st.container(key="title_menu"):
                    st.button(":material/play_arrow: 새 면접 시작", key="title_new", type="primary", width="stretch",
                              on_click=open_window, args=("new",))
                    st.button(":material/folder_open: 이전 면접 이어하기", key="title_resume", width="stretch",
                              on_click=open_window, args=("resume",))
                loaded_count = len(state.get("reports", {}))
                st.caption(f"불러온 리포트 {loaded_count}개 · 이어하기에서 바로 열려요" if loaded_count
                           else "지난 회차 면접리포트.md 가 있으면 이어하기에서 올려 주세요")
    st.stop()

if state.stage in ("pick", "start"):
    mode = state.start_mode
    steps = iter(range(1, 10))

    def heading(text: str):
        st.subheader(f"{next(steps)}. {text}")  # 고르는 순서를 번호 붙은 소제목으로

    # 맨 위 로고 띠 바로 아래: 새 면접 ↔ 이어하기 전환 (원티드 몽타주 Segmented Control 모양 · hover_css).
    # 창 제목 · '타이틀로' 버튼 대신 — 지금 어느 창인지는 전환 버튼이, 타이틀로는 로고 띠가 맡는다.
    state.mode_switch = mode
    st.segmented_control("면접 방식", list(MODE_LABELS), key="mode_switch", format_func=MODE_LABELS.get,
                         required=True, on_change=switch_window, label_visibility="collapsed", width="stretch")

    window = st.container(border=True, key="start_window")

    job = state.get("job") or default_job()
    if mode == "new":
        with window:
            heading("직군")
            for column, name in zip(st.columns(len(coach.JOBS)), coach.JOBS):
                mark = ":material/check: " if name == job else ""
                if column.button(mark + name + ("" if PERSONAS[name] else " (준비 중)"), key=f"pick_job_{name}", width="stretch",
                                 type="primary" if name == job else "secondary"):
                    if not PERSONAS[name]:
                        with st.container(key="job_notice"):  # 배경은 스플래시 판과 같은 색 (hover_css)
                            st.info(f"'{name}' 직군 모드는 준비 중이에요. 면접관 페르소나가 아직 없어요.")
                    elif name != job:
                        reset(name, coach.DEFAULT_FIELD)  # 직군을 바꾸면 아래 칸을 새로 (불러온 리포트 · 그룹 · 태그는 남는다)
                        state.start_mode = "new"
                        st.rerun()
            # 면접관 타입 고르기 (직군에 타입이 둘 이상일 때): 새 면접 ↔ 이어하기 전환과 같은 Segmented Control 모양.
            # 고른 값은 위젯 칸이 아닌 persona_type 에 둔다 (타이틀에 다녀와도 남게)
            ptypes = coach.persona_type_names(job)
            if state.get("persona_type") not in ptypes:
                state.persona_type = ptypes[0] if ptypes else None
            ptype = state.persona_type
            if len(ptypes) > 1:
                heading("면접관")

                def pick_persona_type():
                    state.persona_type = state.persona_switch

                def persona_label(name: str) -> str:  # 타입 이름 옆에 태그 배지 (PERSONA_TAGS)
                    tag = PERSONA_TAGS.get(job, {}).get(name)
                    return f"{name} :blue-badge[{tag}]" if tag else name

                state.persona_switch = ptype
                st.segmented_control("면접관 타입", ptypes, key="persona_switch", required=True, on_change=pick_persona_type,
                                     format_func=persona_label, label_visibility="collapsed", width="stretch")
            # 고른 면접관(페르소나): 머리줄(누구 · 진행 방식 한 줄)은 카드 밖에, 소개(PERSONA_CARDS 의 직군 → 타입)는
            # 칸마다 회색 카드 하나씩 2열로 — 왼쪽 열 성격 · 주목하는 인재상, 오른쪽 열 그 밖의 칸 (평가 항목 · 평가 포인트 등,
            # prompts.py 에 적은 순서 · 칸 이름을 바꾸거나 더해도 그대로 보인다). 같은 줄의 두 카드는 높이를 맞춘다.
            # 소개가 없으면 페르소나 글을 문장마다 나눠 보인다 (prompts.py 글 그대로 · 읽기만).
            # 면접 진행 방식 · 말투는 화면에 보이지 않는 설정이라 PERSONA_TYPES 의 persona 글에만 있다
            lines = coach.persona_lines(job, ptype)
            with st.container(key="persona_head"):
                st.markdown(f":material/support_agent: **{job} 면접관** · {lines[0]}" if lines else f"**{job} 면접관**")
                st.caption(":material/forum: 지원자의 성장을 위해 심층 꼬리 질문 1개와 답변 직후 피드백을 제공해요."
                           if coach.persona_of(job, ptype)["style"] == "feedback"
                           else f":material/forum: 답이 부족하면 꼬리 질문으로 한 번 더 확인해요 (질문마다 {coach.MAX_FOLLOW_UPS}개까지).")
                card = PERSONA_CARDS.get(job, {}).get(ptype)
                if not card and lines[1:]:
                    st.caption("  \n".join(lines[1:]))
            if card:
                left_titles = [t for t in ("성격", "주목하는 인재상") if t in card]
                right_titles = [t for t in card if t not in left_titles]
                with st.container(key="persona_cards"):
                    for row, pair in enumerate(itertools.zip_longest(left_titles, right_titles)):
                        for side, (column, title) in enumerate(zip(st.columns(2, gap="small"), pair)):
                            if title:  # 카드 key 는 자리(줄 · 칸)로 — 한글 칸 이름은 key 글자로 쓸 수 없다
                                with column.container(key=f"persona_card_{row}{side}"):
                                    st.markdown(f"**{title}**\n" + "\n".join(f"- {item}" for item in card[title]))
            # 개발용: .env 에 DEV_MOCK=1 일 때만. AI를 부르지 않고 만점 모의 면접이 끝난 상태로 연다.
            if DEV_MOCK and job == "디자인":
                if st.button(":material/science: 모의 데이터로 열기 (개발용 · 만점)", help="data/mock_perfect.json · 위원 평균 10점 · 종합 100점"):
                    try:
                        mock = coach.load_mock()
                    except (OSError, ValueError, KeyError) as e:
                        st.error(f"모의 데이터를 읽지 못했어요. {e}")
                    else:
                        p = mock["profile"]
                        state.field = p["field"]
                        resume_without_interview(mock, p["name"], job, p["company"], p["company_desc"], p["experience"],
                                                 notice="개발용 모의 데이터(만점)를 열었어요. 글은 모두 예시예요.")
    state.job = job
    field = state.get("field", coach.DEFAULT_FIELD)

    with window:
        if mode == "resume":
            heading("리포트 불러오기")
            # 올리기 칸: 안내 두 줄을 칸 맨 위에 (파일을 올리기 전에 무엇을 올리고 어떻게 되는지 먼저 보이게)
            with st.container(border=True):
                st.markdown("**이어서 할 면접리포트.md 를 올려 주세요.** 회사마다 하나씩, 여러 개 올릴 수 있어요.")
                st.caption("리포트를 올리면 아래에 지난 회차 내용이 채워져요. 올린 리포트는 왼쪽 상태창에서 바꿔 가며 쓸 수 있어요.")
                files = st.file_uploader(
                    "면접리포트.md 올리기",
                    type=["md"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                )
            errors = state.setdefault("report_errors", {})
            # 올리기 칸에서 X 로 지운 파일은 불러온 목록에서도 뺀다.
            # (칸이 화면에 없던 동안에는 비교할 직전 목록이 없어서 아무것도 빼지 않는다)
            now_ids = [f.file_id for f in files or []]
            removed = [fid for fid in state.get("uploader_ids", []) if fid not in now_ids]
            state.uploader_ids = now_ids
            if removed:
                for fid in removed:
                    remove_report(fid)
                st.rerun()
            newest = None
            for f in files or []:
                if f.file_id in state.reports or f.file_id in errors or f.file_id in state.get("report_dismissed", set()):
                    continue  # 올린 파일은 한 번만 읽는다 · 상태창에서 뺀 파일은 다시 넣지 않는다
                try:
                    data = coach.parse_report(f.getvalue().decode("utf-8", errors="replace"))
                except ValueError as e:
                    errors[f.file_id] = f"{f.name}: {e}"
                    continue
                if not PERSONAS.get(data["profile"]["job"]):  # 직군은 리포트를 따라가되, 면접관이 없는 직군은 열 수 없다
                    errors[f.file_id] = f"{f.name}: '{data['profile']['job']}' 직군 모드는 아직 준비 중이에요."
                    continue
                state.reports[f.file_id] = {**data, "file_name": f.name}
                newest = f.file_id
            for f in files or []:
                if f.file_id in errors:
                    st.warning(errors[f.file_id])
            if newest:
                activate_report(newest)  # 마지막으로 올린 리포트로 이어 한다
                st.rerun()
            if len(job_reports()) > 1:
                st.caption(":material/folder_open: 리포트를 여러 개 불러왔어요. 왼쪽 상태창에서 눌러 회사를 바꿀 수 있어요.")

            previous = state.get("previous")
            if not previous:
                st.stop()
            # 지난 회차 요약은 테두리 칸 하나에 모은다
            with st.container(border=True):
                st.markdown(f"**:material/history: {previous['profile']['company']} · {previous['profile']['job']} · {previous['round']}회차** "
                            f":gray[({previous['date']} · {previous['profile']['field']} 분야)]")
                last_col, total_col = st.columns(2)
                last_col.metric("지난 위원 평균", f"{previous['panel_average']:.1f}/{coach.PANEL_MAX}")
                if previous["total_latest"] is not None:
                    total_col.metric("지난 최신 종합", f"{previous['total_latest']}/{coach.TOTAL_MAX}")
                if previous["next"]:
                    with st.expander("지난번에 고칠 것으로 받은 것"):
                        for item in previous["next"]:
                            st.markdown(f"- {item}")
                if previous["precheck"]:
                    st.caption(f"사전 정보 탐색 체크 · 메모 {len(previous['precheck'])}개도 이어서 채워져요.")
                if coach.criteria_changed(previous):
                    st.warning("지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
                # 면접을 다시 하지 않고 지난 결과로 이어 하기 (동의 체크처럼 직접 체크해야 적용)
                if previous.get("session"):
                    st.checkbox(f"면접 없이 {previous['round']}회차 결과로 이어서 연습하기", key="resume_skip",
                                help=f"체크하면 같은 {previous['round']}회차의 평가 · 재도전 · 점검하기 · 암기 · 리포트부터 이어서 해요. "
                                     f"체크하지 않으면 {coach.next_round(previous)}회차 면접을 새로 시작해요.")
                else:
                    state.resume_skip = False
                    st.caption("이 리포트에는 면접 결과 데이터가 없어서, 면접 없이 이어 하기는 할 수 없어요. (결과 저장 기능 전에 받은 리포트)")

        previous = state.get("previous")
        skipping = bool(previous) and bool(state.get("resume_skip"))
        st.caption(f"이어서 할 회차: **{previous['round']}회차** (면접 없이)" if skipping
                   else f"이번 면접: **{coach.next_round(previous)}회차**")

        if not previous:
            # 1회차는 공통 분야로 시작한다 (일반 역량부터) · 2회차부터 분야를 고른다
            state.field = coach.DEFAULT_FIELD
            st.caption(":material/info: 1회차는 **공통** 분야로 일반 역량부터 점검해요. 리포트를 받아 2회차를 이어 하면 분야를 고를 수 있어요.")
        else:
            # 분야: 리포트로 이어 해도 바꿀 수 있다 (분야를 잘못 골라 진행한 회차를 바로잡기). 바꾸면 이번 회차부터 그 분야로 기록된다.
            heading("분야 선택")

            def pick_start_field():
                state.field = state.start_field

            if state.get("start_field") not in FIELDS:
                state.start_field = field if field in FIELDS else coach.DEFAULT_FIELD
            chosen = st.pills("분야", list(FIELDS), key="start_field", required=True, on_change=pick_start_field,
                              label_visibility="collapsed",
                              help="면접관과 평가 위원회가 이 분야를 고려해요. 리포트로 이어 해도 바꿀 수 있어요.")
            st.caption(f"{chosen} · {FIELDS[chosen]}")
            if chosen == coach.DEFAULT_FIELD:  # 지난 회차를 해 본 뒤라면 분야 면접을 권한다
                st.caption(":material/lightbulb: 지원할 회사의 분야를 고르면 그 분야 질문 · 평가 관점으로 실제 면접에 더 가깝게 연습할 수 있어요.")
            if previous["profile"]["field"] != chosen:
                st.info(f"지난 {previous['round']}회차는 **{previous['profile']['field']}** 분야였어요. "
                        f"{'이어 하는 회차' if skipping else '이번 회차'}부터 **{chosen}** 분야로 기록돼요.")

            if not skipping:
                heading("질문 생성 방식")
                modes = list(coach.QUESTION_MODES.values())
                if state.get("previous_mode") not in modes:
                    state.previous_mode = modes[0]
                st.radio(
                    "질문 생성 방식", modes, key="previous_mode", label_visibility="collapsed",
                    help="같은 질문: 질문별 점수를 지난번과 비교해요 · 섞어서: 지난 질문 2개를 다시 하고 나머지는 새 질문 · "
                         "새 질문: 지금까지 불러온 회차에 안 나온 질문부터 골라요 (모자라면 나온 질문을 다시 넣고 알려 드려요).",
                )
                if previous["profile"]["field"] != chosen and state.get("previous_mode") == coach.QUESTION_MODES["same"]:
                    st.caption("같은 질문으로 다시 하면 질문은 지난번 그대로예요. 새 분야 질문을 받으려면 '섞어서' 나 '새 질문으로' 를 골라 주세요.")

        heading("지원 정보")
        # 시작 버튼은 네 칸이 다 차기 전까지 브라우저에서 비활성화한다 (START_GUARD_JS · 폼은 제출 전 값을 서버로 보내지 않아서).
        # 빈칸 · 글자 수 확인은 아래 started 에서 그대로 한다 (Enter 로 제출하는 경우까지)
        with st.form("start"):
            name = st.text_input("이름 (필수)", key="f_name")
            company = st.text_input("회사 이름 (필수)", key="f_company")
            company_desc = st.text_input(
                "회사 설명 (필수)", key="f_company_desc", help="어떤 서비스를 하는 회사인지 한 줄로 적어 주세요.",
                placeholder="예시: IT, 헬스케어 진단 서비스",  # 칸이 비었을 때만 연한 회색으로 보이고, 적기 시작하면 사라진다
            )
            experience = st.text_area(
                "내 경험 (필수)",
                height=170,
                key="f_experience",
                max_chars=coach.MAX_EXPERIENCE_CHARS,
                placeholder=f"{coach.MAX_EXPERIENCE_CHARS:,}자 이내로 입력해주세요.\n"
                            "예시: 대학 팀 프로젝트에서 중고 거래 앱의 UX/UI 디자인을 맡은 경험이 있습니다. "
                            "사용자 인터뷰 5회를 통해 결제 단계의 이탈 원인을 파악하고 화면 흐름을 3단계에서 2단계로 줄였으며, "
                            "피그마 프로토타입으로 개발자와 함께 사용성 테스트를 진행했습니다.",
                help=f"면접관이 참고할 경험을 {coach.MIN_EXPERIENCE_CHARS}~{coach.MAX_EXPERIENCE_CHARS}자로 적어 주세요.",
            )
            started = st.form_submit_button(
                "지난 결과로 이어서 하기" if state.get("previous") and state.get("resume_skip") else "면접 시작하기",
                type="primary",
            )

        if started:
            name, company, experience = name.strip(), company.strip(), experience.strip()
            company_desc = company_desc.strip()
            if not name or not company or not company_desc or not experience:
                st.warning("이름 · 회사 이름 · 회사 설명 · 내 경험을 모두 적어 주세요.")
            elif len(experience) < coach.MIN_EXPERIENCE_CHARS:
                st.warning(f"내 경험을 {coach.MIN_EXPERIENCE_CHARS}자 이상 적어 주세요. (지금 {len(experience)}자)")
            elif state.get("previous") and state.get("resume_skip"):
                resume_without_interview(state.previous, name, job, company, company_desc, experience)
            else:
                previous = state.get("previous")
                mode = next((k for k, v in coach.QUESTION_MODES.items() if v == state.get("previous_mode")), "new")
                # 지금까지 나온 질문: 불러온 이 직군 리포트 + 이어 하는 리포트 (새 질문은 이걸 피해서 고른다)
                asked = {q for r in [*job_reports().values(), *([previous] if previous else [])] for q in r["questions"]}
                try:
                    bank = coach.load_questions()
                    questions, note = coach.plan_questions(
                        bank, job, state.get("field", coach.DEFAULT_FIELD), f"{company} {company_desc}",
                        mode if previous else "new", previous["questions"] if previous else None, asked,
                    )
                    if note:
                        state.notice = note
                except (OSError, ValueError, KeyError):
                    st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
                else:
                    state.profile = {
                        "name": name,
                        "field": state.get("field", coach.DEFAULT_FIELD),
                        "job": job,
                        "company": company,
                        "company_desc": company_desc,
                        "experience": experience,
                        "persona_type": state.get("persona_type"),  # 면접관 타입 (새 면접 창에서 고른 것)
                    }
                    state.questions = questions
                    state.round = coach.next_round(previous)
                    if previous:
                        restore_precheck(previous["precheck"])
                    state.q_index = 0
                    state.follow_ups = 0
                    state.understanding = None
                    state.evaluation = None
                    state.pop("clue_set", None); state.pop("clue_round", None)  # 새 평가에서 실마리를 다시 찾는다
                    state.retries = {}
                    state.retry_history = {}
                    state.memo_edits, state.memo_reviews = {}, {}  # 고친 대본 · 검토 내역은 질문이 바뀌면 맞지 않는다
                    state.last_question = None
                    state.last_suggest = None
                    state.highlights = {}
                    state.strategies = {}
                    state.retry_counts = {}
                    state.verdict_open = False
                    state.messages = [
                        {"role": "assistant", "content": f"{name} 님, 면접을 시작하겠습니다."},
                        question_message(0),
                    ]
                    # 지난 회차와 같은 질문 수 (브리핑 안내 · 같은 질문은 평가 뒤 질문별 비교)
                    state.same_questions = bool(previous) and [q["question"] for q in questions] == list(previous["questions"])
                    state.kept_questions = sum(q["question"] in set(previous["questions"]) for q in questions[1:]) if previous else 0
                    state.stage = "briefing"
                    st.rerun()
    st.stop()


# ── 면접 브리핑 ─────────────────────────────────────────────
if state.stage == "briefing":
    profile = state.profile
    st.title("면접 브리핑")
    with st.container(border=True):
        st.markdown(f"**:material/business: 회사** · {profile['company']} ({profile['company_desc']})")
        st.markdown(f"**:material/explore: 분야** · {coach.field_of(profile)} ({FIELDS[coach.field_of(profile)]})")
        st.markdown(f"**:material/work: 직군** · {profile['job']} 신입 · {state.round}회차")
        st.markdown(f"**{AVATARS['assistant']} 면접관** · {coach.persona_summary(profile['job'], profile.get('persona_type'))}")
        kinds = " → ".join(
            q["type"] + (" :material/explore:" if q.get("field", coach.DEFAULT_FIELD) != coach.DEFAULT_FIELD else "")
            for q in state.questions
        )
        field_count = sum(1 for q in state.questions if q.get("field", coach.DEFAULT_FIELD) != coach.DEFAULT_FIELD)
        if field_count:
            kinds += f" · :material/explore: {coach.field_of(profile)} 분야 질문 {field_count}개"
        st.markdown(f"**:material/quiz: 질문** · {coach.TOTAL_QUESTIONS}개 ({kinds})")
        if state.get("same_questions"):
            st.caption("지난 회차와 같은 질문이에요. 평가 후 질문별로 점수를 비교해 드려요.")
        elif state.get("kept_questions"):
            st.caption(f"자기소개 말고 지난 회차 질문 {state.kept_questions}개가 다시 나와요. 그 질문은 평가 후 점수를 비교해 드려요.")
    st.markdown(
        f"- 질문은 한 번에 하나씩 나와요. 답이 부족하면 면접관이 **꼬리 질문을 최대 {coach.MAX_FOLLOW_UPS}개** 해요.\n"
        f"- 답은 한 번에 **{coach.MAX_ANSWER_CHARS:,}자**까지 쓸 수 있어요.\n"
        "- 면접이 끝나면 위원 4명이 평가하고, 점수가 낮은 질문은 다시 도전할 수 있어요.\n"
        "- 새로고침하면 진행 기록이 사라져요. 평가 뒤 위쪽 :material/description: 리포트 저장하기 버튼에서 면접리포트.md 를 받아 두세요."
    )
    if st.button("면접을 시작하겠습니다.", type="primary", width="stretch"):
        state.stage = "interview"
        st.rerun()
    st.caption(":material/arrow_back: 회사 · 경험을 고치려면 위쪽 '뒤로' 를 눌러 주세요. 적은 내용은 그대로 남아 있어요.")
    st.stop()


# ── 면접 화면 ───────────────────────────────────────────────
profile = state.profile
for state_key, empty in (
    ("highlights", {}), ("last_suggest", None), ("last_question", None), ("previous", None), ("round", 1),
    ("strategies", {}), ("retry_counts", {}), ("verdict_open", False), ("memo_results", {}), ("memo_best", {}),
    ("speak_logs", {}), ("reports", {}), ("retry_history", {}), ("memo_edits", {}), ("memo_reviews", {}),
):
    if state_key not in state:  # 이 기능이 생기기 전에 시작한 세션도 열리게
        state[state_key] = empty
if state.get("notice"):
    st.info(state.pop("notice"))


def memo_summary() -> dict:
    """암기 탭 기록 요약 (체크리스트용): 말하기 타이머로 기록한 횟수 · 대본을 고친 질문 수 · 실전 시뮬레이션을 확인한 질문 수."""
    # 대본 고치기 · 텍스트 · 말하기는 이번 회차 질문만 센다 (다른 질문은 아래 other 로 따로)
    def mine(key: str) -> bool:
        return key.split(":")[0].isdigit()

    speak = sum(len(v) for key, logs in state.get("speak_logs", {}).items() if mine(key)
                for v in (logs.values() if isinstance(logs, dict) else [logs]))
    spoken = len({key.split(":")[0] for key, logs in state.get("speak_logs", {}).items() if mine(key) and logs})
    edited = len({key.split(":")[0] for key in state.get("memo_edits", {}) if mine(key)})
    checked = len({key.split(":")[0] for key in state.get("memo_results", {}) if mine(key)})
    # 다른 질문 연습: id 가 x 로 시작하는 질문에 대본을 고치거나 · 시뮬레이션 · 말하기를 한 질문 수
    other_ids = {q["id"] for q in other_questions()} if state.get("questions") else set()
    other = len({key.split(":")[0] for src in ("memo_edits", "memo_results", "speak_logs")
                 for key in state.get(src, {}) if key.split(":")[0] in other_ids})
    return {"speak": speak, "spoken": spoken, "edited": edited, "checked": checked, "other": other,
            "other_total": len(other_ids)}


def checklist_rows(report_done: bool | None = None) -> list[dict]:
    """단계 체크리스트 (탭 6개 + 리포트). 진행 막대 · 리포트 창 체크리스트 · 마침 안내가 같이 쓴다."""
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []
    ev = state.get("evaluation")
    clues = coach.clue_status(ev, state.get("retries", {}), state.get("retry_counts", {}),
                              state.get("clue_set"), state.get("clue_round", 1)) if ev else None
    return coach.report_checklist(
        state.get("messages", []), ev, clues, bool(state.get("verdict_open")), memo_summary(),
        state.get("last_suggest"), state.get("last_question"), precheck_items, current_precheck(precheck_items),
        bool(state.get("report_downloaded")) if report_done is None else report_done,
        retries=state.get("retries", {}), retry_history=state.get("retry_history", {}),
    )


def build_current_report(ev: dict, updated_at: str | None = None) -> str:
    """지금 회차의 면접리포트.md (리포트 창 · 다음 회차 진행이 같이 쓴다)."""
    try:
        precheck_items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        precheck_items = []
    return coach.build_report(
        profile, state.questions, ev, state.retries, state.messages,
        state.last_suggest, state.last_question, state.previous, state.round,
        precheck_items, current_precheck(precheck_items), updated_at, user_now().date(),
        retry_counts=state.retry_counts, understanding=state.understanding,
        retry_history=state.get("retry_history", {}),
        clue_set=state.get("clue_set"), clue_round=state.get("clue_round", 1), memo=memo_summary(),
        verdict_open=bool(state.get("verdict_open")),
        practice=current_practice(),
        past_hidden=[{"question": q, "round": r} for q, r in sorted(hidden_past())],
    )


def hidden_past() -> set[tuple[str, int]]:
    """지운 지난 회차 답 {(질문 글, 회차)}: 리포트에 남은 것 + 이번 세션에서 지운 것."""
    return coach.saved_hidden(past_reports()) | state.get("past_hidden", set())


def past_reports() -> list[dict]:
    """지난 회차 리포트: 불러온 리포트 중 지금 직군 것 + 이어 하는 리포트 (같은 것은 한 번만)."""
    reports = list(job_reports().values())
    if state.get("previous") and all(state.previous is not r for r in reports):
        reports.append(state.previous)
    return reports


def current_practice() -> list[dict]:
    """리포트에 남길 연습 대본: 지난 회차 대본 + 이번 회차 암기 탭에서 고치거나 직접 쓴 대본 (질문 글 기준).
    다음 회차의 암기 탭 '다른 질문' 에서 '내 연습 대본 (n회차)' 로 다시 나온다."""
    texts = {q["question"]: q["question"] for q in state.get("questions", [])}
    by_id = {coach.practice_id(t): t for t in texts}
    by_id.update({q["id"]: q["question"] for q in other_questions()})
    current = {}
    for key, script in state.get("memo_edits", {}).items():
        head = key.split(":")[0]
        if head.isdigit() and 1 <= int(head) <= len(state.get("questions", [])):
            current[state.questions[int(head) - 1]["question"]] = script
        elif head in by_id:
            current[by_id[head]] = script
    return coach.merge_practice(coach.saved_practice(past_reports()), current, int(state.get("round", 1)))


def go_next_round():
    """다음 회차 면접: 지금 회차를 리포트로 만들어 '불러온 리포트' 에 넣고, 그 리포트로 이어 하는 시작 화면을 연다.
    (리포트 파일을 받아 다시 올리는 것과 같은 길. 버튼 콜백이라 다음 실행 전에 돈다.)"""
    data = coach.parse_report(build_current_report(state.evaluation))
    data["file_name"] = coach.report_file_name(profile["company"], profile["job"], state.round, user_now().date())
    fid = f"round-{state.round}-{time.time_ns()}"
    reset(profile["job"], coach.field_of(profile))
    state.reports[fid] = data
    activate_report(fid)  # 시작 화면 칸을 채우고 '이번 면접: 다음 회차' 로
    state.stage = "start"


next_round_no = coach.next_round({"round": state.round})
st.title(f"{profile['company']} · {coach.field_of(profile)} · {profile['job']} 신입 면접 · {state.round}회차")
def field_examples() -> str:
    """분야 예시 이름 몇 개 (공통 분야 추천 문장용)."""
    return " · ".join(name for name in FIELDS if name != coach.DEFAULT_FIELD)


def ask_report():
    state.open_report = True  # 창은 아래(함수를 다 정의한 뒤)에서 연다


# 다음 회차 · 리포트 버튼을 한 줄에 (리포트는 탭이 아니라 넓은 창으로 본다)
with st.container(horizontal=True, gap="small"):
    next_clicked = st.button(f":material/skip_next: {next_round_no}회차 면접 진행하기", key="next_round",
                             help="지금 회차를 리포트로 남기고, 같은 회사로 다음 회차 면접을 시작해요.")
    st.button(":material/description: 리포트 저장하기", key="open_report_btn", on_click=ask_report,
              help="면접리포트.md 를 미리 보고 내려받아요. 다음 회차 시작 화면에 올리면 이어서 할 수 있어요.")
if next_clicked:
    if not state.get("evaluation"):
        st.info("위원 4명에게 평가받은 뒤에 다음 회차 면접을 진행할 수 있어요.")
    else:
        state.open_next_round = True  # 안내 창은 아래(함수를 다 정의한 뒤)에서 연다


def next_round_dialog():
    """'n회차 면접 진행하기' 안내 창: 오른쪽 위 X 로 닫고(머무르기), 아래 [저장하기] [n회차 시작하기].
    제목에 회차 숫자가 들어가서 열 때마다 대화 상자를 만든다."""
    @st.dialog(f"{next_round_no}회차 면접 진행하기")
    def body():
        st.write(f"{next_round_no}회차로 넘어가면 지금 화면의 기록은 사라지고, 왼쪽 '불러온 리포트' 에 "
                 f"{state.round}회차로 남아요. 목록은 새로고침하면 사라지니 먼저 리포트를 저장해 두세요.")
        if coach.field_of(profile) == coach.DEFAULT_FIELD:
            st.info(f":material/explore: 이번 면접은 **공통** 분야였어요. {next_round_no}회차 시작 화면에서 지원할 회사의 분야"
                    f"({field_examples()})를 골라 보세요. 그 분야 질문과 평가 관점으로 연습할 수 있어요.")
        st.caption(":material/lock: 리포트에는 이름 · 회사 · 내 경험 원문 · 면접 대화 · 답변 · 체크리스트 메모가 들어가요. "
                   "다른 사람과 공유할 때 주의해 주세요.")
        # 리포트 창과 같은 규칙: 개인정보 안내를 확인해야 저장 버튼이 켜진다 (사용자 요청 — disabled 예외)
        agreed = st.checkbox("위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.", key="next_agree")
        file_name = coach.report_file_name(profile["company"], profile["job"], state.round, user_now().date())
        save_col, go_col = st.columns(2)
        save_col.download_button(
            ":material/download: 저장하기", data=build_current_report(state.evaluation, user_now().strftime("%Y-%m-%d %H:%M")),
            file_name=file_name, mime="text/markdown", disabled=not agreed, width="stretch",
            on_click=mark_report_downloaded, key="next_round_save",
        )
        if go_col.button(f"{next_round_no}회차 시작하기", type="primary", width="stretch", key="next_round_go"):
            go_next_round()
            st.rerun()  # 창 안 버튼은 창만 다시 그리므로 화면 전체를 다시 그린다
        if not agreed:
            st.caption(":material/info: 안내를 확인하고 체크하면 저장하기 버튼이 켜져요. 저장하지 않고 시작해도 돼요.")
        elif state.get("report_downloaded"):
            st.caption(":material/check: 리포트를 저장했어요.")

    body()

def show_messages():
    for message in state.messages:
        with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
            st.markdown(message["content"])


# ── 형광펜 ─────────────────────────────────────────────────
# 색상 계열이 서로 겹치지 않는 밝은 바탕 4개. 글자는 모두 진한 색이라 잘 보인다.
HIGHLIGHT_COLORS = {
    "specific": "#FFE45C",   # 노랑 — 구체성
    "relevance": "#8CCBFF",  # 하늘 — 직무 연관
    "structure": "#9BE89B",  # 연두 — 구조
    "evidence": "#FFADD2",   # 분홍 — 근거 · 검증
}
HIGHLIGHT_TEXT = "#171719"  # 밝은 바탕 위 진한 글자


def ai_note(what: str = "AI가 쓴 의견"):
    """AI가 만든 내용 표시 (ui-ux-pro-max: AI Interaction · Disclaimer)."""
    st.caption(f":material/smart_toy: {what}이에요. 사실과 다를 수 있으니 직접 확인해 주세요.")


HIGHLIGHT_CSS = f"""<style>
.hl {{ overflow-wrap: anywhere; }}
.hl details {{ display: inline; }}
.hl summary {{ display: inline; cursor: pointer; list-style: none; }}
.hl summary::-webkit-details-marker {{ display: none; }}
.hl .mark {{ color: {HIGHLIGHT_TEXT}; padding: 1px 3px; border-radius: 4px; line-height: 2;
  box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
.hl .chip {{ color: {HIGHLIGHT_TEXT}; font-size: 0.72em; font-weight: 600; padding: 0 4px;
  margin-left: 3px; border-radius: 3px; vertical-align: 1px; }}
.hl .detail {{ display: block; margin: 4px 0 8px; padding: 6px 10px; font-size: 0.9em;
  border-left: 3px solid #888; }}
</style>"""


def highlight_background(tags: list[str]) -> str:
    """기준 1개면 그 색, 여러 개면 색을 사선 줄무늬로 섞는다."""
    colors = [HIGHLIGHT_COLORS[t] for t in tags]
    if len(colors) == 1:
        return colors[0]
    stops = ", ".join(f"{c} {i * 6}px {(i + 1) * 6}px" for i, c in enumerate(colors))
    return f"repeating-linear-gradient(135deg, {stops})"


def chip(tag: str) -> str:
    return f'<span class="chip" style="background:{HIGHLIGHT_COLORS[tag]}">{coach.CRITERIA[tag]}</span>'


HIGHLIGHT_COLOR_NAMES = {"specific": "노랑", "relevance": "하늘", "structure": "연두", "evidence": "분홍"}
_legend_count = [0]  # 한 화면에 형광펜이 여러 개라 기준지표 칸마다 다른 key (실행마다 0부터)


def show_legend(question: dict):
    st.html(HIGHLIGHT_CSS + '<div class="hl">' + " ".join(chip(t) for t in HIGHLIGHT_COLORS)
            + " <small>· 줄무늬는 여러 기준 · 문장을 누르면 상세 보기 · 기준 판단은 AI가 했어요</small></div>")
    _legend_count[0] += 1
    with st.popover(":material/rule: 기준지표", type="tertiary", key=f"hl_rule_{_legend_count[0]}",
                    help="AI가 문장에 형광펜을 칠할 때 따른 기준이에요."):
        st.markdown("**형광펜 기준 판단 근거**")
        st.caption("미리 정해 둔 기준이에요. AI는 이 표와 아래 '보는 점' 으로 문장마다 기준을 0~4개 골라 칠해요.")
        rows = coach.highlight_criteria()
        if rows:
            st.table([{"색": HIGHLIGHT_COLOR_NAMES[r["key"]], "기준": r["name"], "이런 문장에 칠해요": r["rule"],
                       "채점": f"0~{coach.CRITERION_MAX}점"} for r in rows], hide_index=True)
        else:
            st.info("기준표를 읽지 못했어요. prompts.py 의 형광펜 지시문 [기준] 줄 모양을 확인해 주세요.")
        st.markdown(f"**이 질문에서 보는 점:** {question['point']}")
        st.caption("문장을 누르면 AI가 그 기준을 고른 이유 1문장을 볼 수 있어요. 판단은 AI가 했으니 직접 확인해 주세요.")


def show_highlighted(sentences: list[str], numbers: list[int], marks: dict):
    parts = []
    for sentence, no in zip(sentences, numbers):
        mark = marks.get(no, {"tags": [], "why": ""})
        text = html.escape(sentence)
        if mark["tags"]:
            names = " · ".join(coach.CRITERIA[t] for t in mark["tags"])
            summary = (f'<span class="mark" style="background:{highlight_background(mark["tags"])}">{text}</span>'
                       + "".join(chip(t) for t in mark["tags"]))
        else:
            names = "해당 기준 없음"
            summary = text
        detail = f"<b>{names}</b>" + (f" — {html.escape(mark['why'])}" if mark["why"] else "")
        parts.append(f'<details><summary>{summary}</summary><span class="detail">{detail}</span></details>')
    st.html(HIGHLIGHT_CSS + '<div class="hl">' + " ".join(parts) + "</div>")


def get_highlight(cache_key: str, blocks: list[dict]) -> dict | None:
    """형광펜 결과를 한 번만 만들고 저장해 둔다. blocks: [{question, point, sentences}]."""
    if cache_key not in state.highlights:
        user_input, numbers = coach.build_highlight_input(blocks)

        def store(raw):
            state.highlights[cache_key] = {"numbers": numbers, "marks": coach.summarize_highlight(raw)}

        if not call_ai("문장마다 기준을 표시하고 있어요...", coach.build_highlight(profile), user_input,
                       HIGHLIGHT_SCHEMA, "highlight", store):
            return None
    return state.highlights[cache_key]


ACTION_ICONS = {"추가": ":material/add:", "수정": ":material/edit:", "축약": ":material/content_cut:", "삭제": ":material/delete:"}
SPEAK_STEP_ICONS = {1: ":material/menu_book:", 2: ":material/visibility:", 3: ":material/visibility_off:"}


def show_strategy(place: str, cache_key: str, no: int, scores: dict, weak: str, answer: str, ev: dict):
    """20점 미만인 답에 '+N점 전략 가이드'. 더 받을 수 있는 점수는 코드가 계산하고, 전략 글은 AI가 쓴다.
    cache_key 로 한 번 만든 전략을 저장해 두고, 같은 답이면 평가 · 재도전 탭이 같이 쓴다."""
    gap = coach.strategy_gap(scores)
    if not gap:
        return
    st.markdown(f"**:material/trending_up: +{sum(gap.values())}점 전략 가이드**")
    st.caption(" · ".join(f"{coach.CRITERIA[key]} +{g}" for key, g in gap.items()))
    if cache_key in state.strategies:
        ai_note("점수는 앱이 계산했고, 전략 글은 AI가 쓴 의견")
    if cache_key not in state.strategies:
        # 같은 답의 버튼이 평가 · 재도전 탭에 함께 그려질 수 있어서 위치(place)를 key 에 넣는다.
        if st.button("전략 가이드 받기", key=f"strategy_{place}_{cache_key}"):
            question = state.questions[no - 1]

            def store(raw):
                state.strategies[cache_key] = coach.summarize_strategy(raw, scores)

            if call_ai(
                "점수를 올릴 전략을 찾고 있어요...",
                coach.build_strategy(profile, question, {"scores": scores, "weak": weak}, ev),
                answer or "(답 없음)", STRATEGY_SCHEMA, "strategy", store,
            ):
                st.rerun()
        return
    # 만든 뒤에는 카드를 접기 칸 안에 넣는다 (부르는 곳이 접기 칸 안이 아니어야 한다 — 접기 칸은 겹칠 수 없음)
    items = state.strategies[cache_key]
    with st.expander(f":material/tips_and_updates: 전략 가이드 카드 {len(items)}개 보기"):
        for item in items:
            with st.container(border=True):
                st.markdown(f"**{item['name']}** {item['score']}/{coach.CRITERION_MAX} · **+{item['gain']}점 여지**")
                for t in item["tips"]:
                    line = f"{ACTION_ICONS.get(t['action'], ':material/chevron_right:')} **{t['action']}** · {t['tip']}"
                    if t["target"]:
                        line += f"  \n  ↳ 내 답: \"{t['target']}\""
                    st.markdown(line)
                if not item["tips"]:
                    st.caption("이 기준에 대한 전략을 받지 못했어요.")


def show_perfect_hints(ev: dict):
    """만점일 때 힌트: 평가에 이미 있는 더 다듬을 점 · 다듬은 답 · 확인할 것 (고르는 건 coach.perfect_hints, AI 새 호출 없음)."""
    hints = coach.perfect_hints(ev)
    if not hints:
        st.info("이번 평가에는 더 다듬을 점이 따로 없어요. 이 답들을 그대로 외워 두세요.")
        return
    st.caption("만점이어도 실제 면접에서 한 번 더 다듬을 수 있는 점이에요.")
    ai_note("더 다듬을 점 · 다듬은 답 · 확인할 것은 AI가 평가 때 쓴 의견")
    for hint in hints:
        with st.container(border=True):
            st.markdown(f"**질문 {hint['no']}** · {coach.ANSWER_MAX}/{coach.ANSWER_MAX}점")
            st.caption(hint["question"])
            if hint["weak"]:
                st.markdown(f":material/lightbulb: **더 다듬는다면:** {hint['weak']}")
            if hint["rewrite"]:
                st.markdown("**힌트 답변**")
                st.markdown(f"> {hint['rewrite']}")
            for item in hint["check"]:
                st.markdown(f":material/fact_check: **면접 전 확인:** {item}")


def show_clues(ev: dict):
    """역전의 실마리: 가장 낮은 답 MAX_CLUES 개와 각 답의 가장 낮은 기준. 고르는 건 코드(coach.pick_clues).
    찾은 실마리는 state.clue_set 에 고정해 둔다 (재도전 뒤에도 같은 실마리에 '역전 성공! 전 → 후' 를 보여 주려고).
    실마리를 모두 재도전하면 '역전의 실마리 찾기' 로 최신 점수에서 다시 찾는다."""
    retries, retry_counts = state.get("retries", {}), state.get("retry_counts", {})
    if "clue_set" not in state:
        state.clue_set = coach.pick_clues(ev, retries=retries, retry_counts=retry_counts)
    clues = state.clue_set
    # 만점은 아니지만 재도전을 모두 써서 실마리로 고르지 않은 답 (최신 점수 기준)
    used_up = [a["no"] for a in coach.latest_answers(ev, retries)
               if a["score"] < coach.ANSWER_MAX and retry_counts.get(a["no"], 0) >= coach.MAX_RETRIES]
    if not clues and used_up:
        st.info(f":material/flag: 남은 질문 {', '.join(map(str, used_up))}번은 재도전을 {coach.MAX_RETRIES}번 모두 했어요. "
                "리포트를 받아 다음 회차에서 이어서 연습하거나, 암기 탭에서 말하기 연습으로 다듬어 보세요.")
        return
    if not clues:
        st.success(":material/celebration: 모든 답이 20점 만점이에요.")
        if st.button(":material/lightbulb: 힌트 확인하기", key="perfect_hints"):
            state.perfect_hints_open = not state.get("perfect_hints_open")
            st.rerun()
        if state.get("perfect_hints_open"):
            show_perfect_hints(ev)
        return
    progress = coach.clue_progress(clues, ev, retries, retry_counts)
    clue_round = state.get("clue_round", 1)
    done_count = sum(r["retried"] for r in progress["rows"])
    st.subheader(":material/search: 역전의 실마리를 찾았습니다.")
    st.badge(f"실마리 {clue_round}회차 · {len(clues)}개 중 {done_count}개 재도전 완료",
             icon=":material/check_circle:" if progress["done"] else ":material/update:",
             color="green" if progress["done"] else "blue")
    if state.pop("clue_updated", False):
        st.success(f":material/update: 실마리가 **{clue_round}회차**로 업데이트됐어요. 재도전 점수를 넣은 최신 점수에서 다시 찾았어요.")
    st.caption(f"점수가 가장 낮은 답 {len(clues)}개예요. 여기부터 고치면 점수가 가장 많이 올라요."
               + (f" 재도전을 {coach.MAX_RETRIES}번 모두 한 질문({', '.join(map(str, used_up))}번)은 빼고 골랐어요."
                  if used_up and clue_round > 1 else ""))
    for clue, row in zip(clues, progress["rows"]):
        with st.container(border=True):
            st.markdown(
                f"**질문 {clue['no']}** · {clue['score']}/{coach.ANSWER_MAX}점 · "
                f"가장 약한 기준 **{clue['name']} {clue['criterion_score']}/{coach.CRITERION_MAX}**"
            )
            st.caption(clue["question"])
            if row["up"]:
                st.success(f":material/trending_up: **역전 성공!** {row['before']} → {row['after']}점 (+{row['diff']})")
            used = retry_counts.get(clue["no"], 0)  # 재도전 횟수 (MAX_RETRIES 까지)
            left = used < coach.MAX_RETRIES
            if row["retried"] and not row["up"]:
                more = "한 번 더 도전해 볼 수 있어요." if left else f"재도전을 {coach.MAX_RETRIES}번 모두 했어요."
                st.info(f"재도전 완료 · {row['before']} → {row['after']}점 ({row['diff']:+d}). {more}")
            elif not row["up"]:
                st.markdown(f"**가장 약한 점:** {clue['weak']}")
                st.caption(f"'역전의 기회 잡기' 를 누르면 아래에서 질문 {clue['no']} 의 형광펜 · 전략 가이드를 보며 다시 답할 수 있어요.")
            if not row["up"]:
                # 남은 기회를 버튼에 보여 준다. 0이면 꺼진 버튼 (사용자 요청 — CLAUDE.md 'disabled 금지' 의 예외, 이유는 버튼 글자로)
                remaining = coach.MAX_RETRIES - used
                name = "한 번 더 도전하기" if row["retried"] else "역전의 기회 잡기"
                label = f":material/replay: {name} · 남은 기회 {remaining}/{coach.MAX_RETRIES}"
                if st.button(label, key=f"clue_retry_{clue['no']}", disabled=not left,
                             type="secondary" if row["retried"] or not left else "primary",
                             help=None if left else "이 질문은 재도전 기회를 모두 썼어요. 다음 회차 면접에서 이어서 연습해 보세요."):
                    state.go_retry_no = clue["no"]
                    state.go_tab = RETRY_TAB
                    state.scroll_retry = True  # 아래 '답변 재도전' 으로 내려간다
                    st.rerun()
    # 실마리를 모두 재도전해야 다음 실마리를 찾을 수 있다 (사용자 요청으로 disabled 예외: 못 누르는 이유를 버튼 글자로 보여 줌)
    if progress["done"]:
        if st.button(":material/search: 역전의 실마리 찾기", key="clue_find", type="primary",
                     help="최신 점수(재도전 점수 포함)에서 가장 낮은 답을 다시 찾아요."):
            state.clue_set = coach.pick_clues(ev, retries=retries, retry_counts=retry_counts)
            state.clue_round = clue_round + 1
            state.clue_updated = True  # 다음 화면에서 한 번만 '업데이트됐어요' 를 알린다
            st.rerun()
    else:
        st.button("재도전을 진행해보세요.", key="clue_find", disabled=True,
                  help=f"위 실마리 {len(clues)}개를 모두 재도전하면 다음 실마리를 찾을 수 있어요.")


PANEL_ICONS = {  # 위원 캐릭터 태그 아이콘 (Material 이름은 streamlit/material_icon_names.py 에서 확인)
    "실무 전문가": ":material/construction:",
    "논리 분석가": ":material/psychology:",
    "커뮤니케이션 전문가": ":material/forum:",
    "채용 담당자": ":material/person_search:",
}


def show_panel_cards(panel: list[dict]):
    """위원 캐릭터 태그를 하나 고르면 그 위원의 의견을 카드 하나로 자세히 보여 준다."""
    by_role = {m["role"]: m for m in panel}
    role = st.pills(
        "위원별 의견", list(by_role), key="panel_pick", default=next(iter(by_role)), required=True,
        format_func=lambda r: f"{PANEL_ICONS.get(r, ':material/person:')} {r} · {by_role[r]['score']}",
        help="태그를 눌러 위원 한 명씩 자세히 볼 수 있어요.",
    )
    m = by_role[role]
    with st.container(border=True):
        name_col, score_col = st.columns([3, 1], vertical_alignment="center")
        name_col.markdown(f"#### {PANEL_ICONS.get(role, ':material/person:')} {role}")
        score_col.metric("점수", f"{m['score']}/{coach.PANEL_MAX}", label_visibility="collapsed")
        st.progress(m["score"] / coach.PANEL_MAX)
        st.caption(f"평가 기준 · {PANEL_CRITERIA[role]}")
        st.markdown(f":green[:material/thumb_up:] **좋은 점**  \n{m['good'] or '(의견 없음)'}")
        st.markdown(f":red[:material/report:] **뽑지 말아야 할 이유**  \n{m['against'] or '(의견 없음)'}")


def show_example(question: dict, score: int):
    """만점 예시 답안: 질문 은행에 미리 적어 둔 가상 지원자의 답 (AI 호출 없음 · 내 경험과 무관).
    내 답을 고칠 방향만 참고하도록, 문장을 그대로 외우지 말라고 안내한다."""
    example = question.get("example", "")
    if score >= coach.ANSWER_MAX or not example:
        return
    st.markdown("**만점 예시 답안** · :material/person_book: 가상 지원자")
    st.info("  \n".join(coach.split_sentences(example)))
    st.caption("질문 은행에 미리 적어 둔 예시라 내 경험 · 숫자와 무관해요. "
               "결론 → 상황 · 행동(숫자) → 확인 방법 → 직무 연결 흐름만 참고해서 내 경험으로 고쳐 보세요.")


def show_evaluation(ev: dict):
    # 역전의 실마리 · 형광펜 · 전략 가이드 · 다음 연습에서 고칠 것은 재도전 탭에서 본다 (기능 중복을 줄임)
    totals = coach.total_scores(ev, state.get("retries", {}))
    st.subheader(f":material/gavel: {coach.eval_title(totals, ev['panel_average'])}")
    st.metric("위원 평균", f"{ev['panel_average']:.1f}/{coach.PANEL_MAX}")
    ai_note("점수 합계 · 평균은 앱이 계산했고, 위원 의견 · 약한 점 · 고친 답은 AI가 쓴 의견")
    show_panel_cards(ev["panel"])
    conflict_col, agree_col = st.columns(2)
    with conflict_col.container(border=True, height="stretch"):
        st.markdown(":orange[:material/call_split:] **판단이 갈린 곳**")
        st.write(ev["conflict"] or "(의견 없음)")
    with agree_col.container(border=True, height="stretch"):
        st.markdown(":green[:material/handshake:] **모두 같은 판단**")
        st.write(ev["agree"] or "(의견 없음)")
    with st.expander(":material/table_view: 전체 요약 · 위원 4명 한눈에 보기"):
        # st.table 은 긴 글을 칸 안에서 줄바꿈해서 가로 스크롤이 생기지 않는다 (st.dataframe 은 줄바꿈 옵션이 없음).
        st.table(
            [
                {
                    "위원": m["role"],  # 표 칸은 아이콘을 그리지 못해서 글자만
                    "평가 기준": PANEL_CRITERIA[m["role"]],
                    "뽑지 말아야 할 이유": m["against"],
                    "좋은 점": m["good"],
                    "점수": m["score"],
                }
                for m in ev["panel"]
            ],
            hide_index=True,
        )
    with st.expander(":material/menu_book: 평가 기준과 근거 보기"):
        try:
            st.markdown(coach.load_panel_rationale())
        except OSError:
            st.error("평가 기준 근거 문서(data/평가기준_근거.md)를 읽지 못했어요.")

    if state.previous:
        prev = coach.compare_previous(state.previous, ev, state.questions, state.retries)
        st.subheader(f"지난 면접({prev['round']}회차 · {prev['date']})과 비교")
        if prev["criteria_changed"]:
            st.warning("지난 회차와 평가 기준이 달라서 점수 비교가 정확하지 않을 수 있어요.")
        panel_col, total_col = st.columns(2)
        panel_col.metric("위원 평균", f"{prev['panel_after']:.1f}/{coach.PANEL_MAX}", delta=round(prev["panel_diff"], 1))
        if prev["total_before"] is not None:
            total_col.metric(
                "최신 종합", f"{prev['total_after']}/{coach.TOTAL_MAX}", delta=prev["total_after"] - prev["total_before"]
            )
        if prev["rows"]:
            st.table(prev["rows"], hide_index=True)
        else:
            st.caption("지난 면접과 같은 질문이 없어서 질문별 비교는 없어요.")

    st.subheader("답변별 점수")
    # 질문마다 나온 회차 태그: 색은 그 회차의 분야 (공통 회색 · 헬스케어 하늘색 …), 이번 회차는 '· 현재'
    # 지난 회차에만 나온 질문은 '전체 회차 보기' 에서
    history = coach.question_history(past_reports())
    current_round = int(state.round)
    used = {coach.field_of(profile)} | {row["field"] for rows in history.values() for row in rows}
    with st.container(key="eval_legend"):
        st.caption("태그 색은 그 회차의 분야예요: "
                   + " · ".join(f":{field_badge(f)}-badge[{f}]" for f in FIELDS if f in used or f == coach.DEFAULT_FIELD)
                   + " · 글자는 그 질문이 나온 회차 (이번 회차는 '· 현재')")
    current_texts = {q["question"] for q in state.questions}
    past_only = {t: rows for t, rows in history.items() if t not in current_texts}
    show_all = False
    if past_only:
        options = [f"{current_round}회차만 보기", "전체 회차 보기"]
        if state.get("eval_rounds") not in options:
            state.eval_rounds = options[0]
        show_all = st.segmented_control(
            "보기", options, key="eval_rounds", required=True, label_visibility="collapsed",
            help="전체 회차 보기: 이번 회차에 나오지 않은 지난 회차 질문과 그때 답도 함께 보여요 (점수는 이번 회차 종합에 들어가지 않아요).",
        ) == options[1]

    def tags(text: str, with_current: bool) -> str:
        rounds = {row["round"] for row in history.get(text, [])} - {current_round}
        rounds = sorted(rounds | ({current_round} if with_current else set()))
        fields = {row["round"]: row["field"] for row in history.get(text, [])}
        fields[current_round] = coach.field_of(profile)
        return " ".join(
            f":{field_badge(fields.get(r, coach.DEFAULT_FIELD))}-badge[{r}회차{' · 현재' if r == current_round else ''}]"
            for r in rounds
        )

    for a in ev["answers"]:
        label = f"질문 {a['no']} · {a['score']}/{coach.ANSWER_MAX}점 {tags(a['question'], True)}"
        with st.expander(label, expanded=a["needs_rewrite"]):
            st.caption(a["question"])
            st.write(" · ".join(f"{name} {a['scores'][key]}" for key, name in coach.CRITERIA.items()))
            st.markdown("**내 답**")
            show_answer(coach.answer_text(state.messages, a["no"] - 1), state.questions[a["no"] - 1], f"eval:{a['no']}", False)
            st.markdown(f"**가장 약한 점:** {a['weak']}")
            show_example(state.questions[a["no"] - 1], a["score"])
            if a["score"] < coach.ANSWER_MAX:
                if st.button(":material/replay: AI 코칭을 반영해 재도전으로 역전의 기회 잡기", key=f"eval_retry_{a['no']}",
                             type="primary", help="재도전 탭에서 형광펜 · 전략 가이드를 보며 이 질문에 다시 답해요."):
                    state.go_retry_no = a["no"]
                    state.go_tab = RETRY_TAB
                    st.rerun()

    if not show_all:
        return
    # 지난 회차에만 나온 질문: 그 회차의 최신 답 · 점수 (읽기만 · 이번 회차 종합 점수에는 들어가지 않는다)
    st.markdown("**지난 회차에만 나온 질문**")
    st.caption("지난 회차 기록이에요. 점수는 그 회차 최신 점수이고, 이번 회차 종합 점수에는 들어가지 않아요. "
               ":material/psychology: 암기 탭의 '다른 질문' 에서 연습할 수 있어요.")
    for text, rows in sorted(past_only.items(), key=lambda kv: -kv[1][-1]["round"]):
        last = rows[-1]
        score = f"{last['score']}/{coach.ANSWER_MAX}점" if isinstance(last["score"], int) else "점수 없음"
        with st.expander(f"지난 {last['round']}회차 질문 · {score} {tags(text, False)}"):
            st.caption(text)
            st.markdown(f"**{last['round']}회차 내 답**")
            st.markdown("  \n".join(coach.split_sentences(last["answer"])) or "(답 없음)")


# 회차 태그 색 (평가 탭 답변별 점수): 분야마다. 헬스케어의 blue 는 hover_css 가 하늘색으로 바꿔 칠한다.
FIELD_BADGES = {coach.DEFAULT_FIELD: "gray", "헬스케어": "blue"}
OTHER_FIELD_BADGE = "violet"  # 색을 아직 정하지 않은 분야


def field_badge(field: str) -> str:
    return FIELD_BADGES.get(field, OTHER_FIELD_BADGE)


def highlight_toggle(key: str) -> bool:
    """답 하나에만 형광펜을 켜고 끄는 스위치."""
    return st.toggle(":material/ink_highlighter: 형광펜 모드", key=key, help="이 답의 문장마다 어떤 기준과 연결되는지 색으로 보여 줘요.")


def show_answer(text: str, question: dict, cache_key: str, highlight_on: bool):
    """답 하나를 보여 준다. highlight_on 이면 형광펜으로.
    cache_key 가 같으면 (예: 평가 탭과 재도전 탭의 같은 답) 한 번 만든 형광펜을 같이 쓴다."""
    sentences = coach.split_sentences(text)
    block = {"question": question["question"], "point": question["point"], "sentences": sentences}
    highlight = get_highlight(cache_key, [block]) if highlight_on and sentences else None
    if highlight:
        show_legend(question)
        show_highlighted(sentences, highlight["numbers"][0], highlight["marks"])
    else:
        st.markdown("  \n".join(sentences) or "(답 없음)")  # 한 문장씩 줄을 바꿔 읽기 쉽게


def record_retry(no: int, attempt: dict, original_score: int):
    """재도전 하나를 기록에 더하고, 반영할 재도전(최고 점수)을 다시 고른다 (고르는 건 coach.reflected_retry).
    재도전 탭 · 암기 탭의 재도전 검토가 같이 쓴다."""
    history = state.setdefault("retry_history", {}).setdefault(no, [])
    history.append(attempt)
    best = coach.reflected_retry(original_score, history)
    if best:
        state.retries[no] = best
    else:
        state.retries.pop(no, None)  # 모두 처음 점수 이하 → 처음 점수 반영


def show_failed_retries(no: int, original_score: int):
    """반영되지 않은 재도전을 접기 칸으로 (최고 점수만 종합 점수에 들어간다)."""
    fails = coach.failed_retries(original_score, state.get("retry_history", {}).get(no, []))
    if not fails:
        return
    with st.expander(f":material/history: 반영 안 된 재도전 {len(fails)}번 보기"):
        st.caption("종합 점수에는 가장 높은 점수만 들어가요. 아래는 반영되지 않은 재도전 기록이에요.")
        for n, r in fails:
            with st.container(border=True):
                st.markdown(f"**{n}번째 재도전** · {original_score} → {r['score']}점 ({r['score'] - original_score:+d})")
                st.markdown("\n".join(f"> {line}" for line in r["answer"].splitlines()))
                st.caption(f"AI 의견 · 약한 점: {r['weak']}")


COACH_TREND_ICONS = {"up": ":green[:material/trending_up:]", "down": ":red[:material/trending_down:]",
                     "same": ":gray[:material/trending_flat:]"}


def coach_card_height(rows: list[dict]) -> int:
    """위원 코치 카드 높이(px): 글 길이로 줄 수를 넉넉히 어림해 가장 긴 카드에 맞춘다.
    (Streamlit 은 서버에서 글 높이를 잴 수 없어서 어림한다. 넉넉하면 아래 여백만 조금 남고, 모자라면 카드 안에 스크롤이 생긴다.)
    두 칸 너비에서 본문은 한 줄 약 17자 · 24px, 작은 글씨는 약 20자 · 21px 로 본다."""
    def lines(text: str, per_line: int) -> int:
        return max(1, math.ceil(len(text) / per_line))

    tallest = max(24 + 21 * lines(r["changes"], 20) + 24 * lines(r["message"], 17) for r in rows)
    return 32 + 2 * 16 + tallest + 8  # 위아래 여백 + 줄 사이 간격 + 여유


def show_panel_coaching(before: dict, after: dict):
    """다시 채점 결과 맨 끝: 위원 4명의 코치 피드백 (점수 변화로 coach.panel_coaching 이 고른 고정 문장)."""
    st.markdown("**:material/groups: 위원 코치 피드백**")
    st.caption("기준별 점수 변화로 앱이 고른 코칭이에요. AI가 답을 다시 읽고 쓴 의견은 아니에요.")
    rows = coach.panel_coaching(before, after)
    height = coach_card_height(rows)  # 4장 모두 가장 긴 카드 높이로
    cols = st.columns(2)
    for i, row in enumerate(rows):
        with cols[i % 2].container(border=True, height=height):
            st.markdown(f"{PANEL_ICONS.get(row['role'], ':material/person:')} **{row['role']}**")
            st.caption(row["changes"])
            st.markdown(f"{COACH_TREND_ICONS[row['trend']]} {row['message']}")


def show_retry_result(no: int, ev: dict, index: int, place: str, celebrate: bool = False):
    """재도전 결과 하나 (전 → 후). 재도전 탭 · 암기 탭의 재도전 검토가 같은 구조로 같이 쓴다.
    index: retry_history 안의 몇 번째 재도전인지. place: 두 탭이 함께 그려져도 칸 key 가 겹치지 않게.
    celebrate: 점수가 오르면 '역전 성공!' 을 여기서 띄운다 (재도전 탭은 실마리 카드에만 띄우므로 False)."""
    last = ev["answers"][no - 1]
    question = state.questions[no - 1]
    history = state.get("retry_history", {}).get(no, [])
    result = history[index]
    reflected = state.retries.get(no)  # 종합 점수에는 최고 점수 (coach.reflected_retry)
    diff = coach.compare(last["scores"], result["scores"])
    if diff["diff"] > 0 and celebrate:
        st.success(f":material/celebration: 역전 성공! {diff['before']} → {diff['after']}점으로 {diff['diff']}점 올랐어요.")
    elif diff["diff"] == 0:
        st.info(f"점수가 {diff['after']}점 그대로예요. 아래 약한 점과 전략 가이드를 보고 한 부분만 바꿔 보세요.")
    elif diff["diff"] < 0:  # 진짜로 내려갔을 때만
        st.warning(
            f"{diff['before']} → {diff['after']}점으로 {-diff['diff']}점 내려갔어요. "
            "아래 기준별 변화와 약한 점을 보고 다시 도전해 보세요."
        )
    st.metric("후 점수", f"{diff['after']}/{coach.ANSWER_MAX}", delta=diff["diff"])
    if reflected is result:
        st.caption(":material/check: 이 점수가 종합 점수에 반영돼요 (최고 점수 반영).")
    elif reflected:
        n = history.index(reflected) + 1
        st.caption(f":material/info: 종합 점수에는 {n}번째 재도전의 최고 점수 {reflected['score']}점이 반영돼 있어요.")
    else:
        st.caption(f":material/info: 처음 점수보다 높지 않아서, 종합 점수에는 처음 점수 {last['score']}점이 그대로 반영돼요.")
    # 기준별 전/후 막대 그래프 (숫자는 모두 coach.compare() 가 계산한 값)
    chart = pd.DataFrame(
        {"전": [r["전"] for r in diff["rows"]], "후": [r["후"] for r in diff["rows"]]},
        index=[r["기준"] for r in diff["rows"]],
    )
    st.bar_chart(chart, stack=False, y_label="점수 (0~5)", color=["#C2C4C8", "#4263D6"], height=240)
    st.table(diff["rows"], hide_index=True)
    st.markdown(f"**이번 답의 약한 점:** {result['weak']}")
    ai_note("점수 차이는 앱이 계산했고, 약한 점은 AI가 쓴 의견")
    retry_key = f"retry:{no}:{result['answer']}"  # 형광펜 · 전략은 두 탭이 같은 답이면 같이 쓴다
    with st.expander(":material/edit_note: 다시 쓴 답 보기"):
        show_answer(result["answer"], question, retry_key, highlight_toggle(f"hl_{place}_after_{no}"))
    show_strategy(f"{place}_after", retry_key, no, result["scores"], result["weak"], result["answer"], ev)
    show_panel_coaching(last["scores"], result["scores"])


def show_retry(ev: dict):
    if state.pop("scroll_top", False):
        scroll_to_top()
    show_clues(ev)  # 역전의 실마리는 재도전 탭 맨 위 (평가 탭에서 옮김)
    # '다음 연습에서 고칠 것' 은 처음 평가 때 한 번 만든 글이라 재도전 뒤에 바뀌지 않는다 → 화면에서는 뺀다 (리포트에만)
    st.divider()
    st.subheader(":material/edit_note: 답변 재도전", anchor="retry-answer")
    if state.pop("scroll_retry", False):
        scroll_to_anchor("retry-answer")
    # 고르는 칸은 지금 점수(재도전 최고 점수 반영) 낮은 순 · 비교 기준(last)은 면접 때 처음 답
    original = {a["no"]: a for a in ev["answers"]}
    counts = state.get("retry_counts", {})

    def label(a: dict) -> str:
        first = original[a["no"]]["score"]
        score = f"{first} → {a['score']}" if a["score"] != first else f"{first}"
        return (f"질문 {a['no']} · {score}/{coach.ANSWER_MAX}점 · 재도전 {counts.get(a['no'], 0)}/{coach.MAX_RETRIES} · "
                f"{a['question']}")

    labels = {a["no"]: label(a) for a in coach.retry_order(coach.latest_answers(ev, state.get("retries", {})))}
    no = st.selectbox("다시 답할 질문 (지금 점수 낮은 순)", list(labels), format_func=labels.get, key="retry_no")
    last = original[no]
    question = state.questions[no - 1]
    before = coach.answer_text(state.messages, no - 1)

    history = state.get("retry_history", {}).get(no, [])
    result = history[-1] if history else None   # 화면에는 방금 한 재도전
    comeback = bool(result) and result["score"] > last["score"]  # 역전 성공이면 결과를 맨 위, 역전 전 기록은 맨 아래로

    def show_past():
        st.metric("지난 점수", f"{last['score']}/{coach.ANSWER_MAX}")
        st.markdown(f"**지난 약한 점:** {last['weak']}")
        with st.expander("지난 답 보기"):
            show_answer(before, question, f"eval:{no}", highlight_toggle(f"hl_retry_before_{no}"))
        # 다시 쓰기 전에 참고하도록 지난 답의 전략 가이드 (평가 탭과 같은 결과를 같이 쓴다)
        show_strategy("retry_before", f"eval:{no}", no, last["scores"], last["weak"], before, ev)

    def show_answer_box():
        st.markdown("**이제, 당신의 차례입니다.**")
        new_answer = st.text_area(
            "다시 답하기", height=180, key=f"retry_answer_{no}", max_chars=coach.MAX_ANSWER_CHARS
        )
        used = state.retry_counts.get(no, 0)
        st.caption(f"이 질문 재도전 {used}/{coach.MAX_RETRIES}번")
        if st.button("다시 채점", type="primary"):
            if not new_answer.strip():
                st.info("다시 쓴 답을 적은 뒤 눌러 주세요.")
            elif used >= coach.MAX_RETRIES:
                st.info(
                    f"이 질문은 재도전을 {coach.MAX_RETRIES}번 모두 했어요. 다른 질문에 도전하거나, "
                    "리포트를 받아 다음 회차에서 이어서 연습해 보세요."
                )
            else:
                def store(raw):
                    attempt = {"answer": new_answer.strip(), **coach.summarize_retry(raw)}
                    record_retry(no, attempt, last["score"])
                    state.retry_counts[no] = used + 1
                    if attempt["score"] > last["score"]:
                        state.scroll_top = True  # 역전 성공: 결과가 맨 위에 오므로 페이지 맨 위로

                if call_ai(
                    "다시 쓴 답을 채점하고 있어요...",
                    coach.build_retry(profile, question, before, last["weak"]),
                    new_answer.strip(), RETRY_SCHEMA, "retry", store,
                ):
                    st.rerun()

    def show_result():
        # 점수가 오르면 '역전 성공!' 은 맨 위 역전의 실마리 카드에만 띄운다 (여기서는 후 점수 +n 으로만 보여 줌)
        show_retry_result(no, ev, len(history) - 1, "retry")

    if comeback:
        show_result()
        st.divider()
        show_answer_box()
        st.divider()
        st.markdown("**:material/history: 역전 전 기록**")
        st.caption("역전하기 전의 점수와 답이에요. 지금 점수는 위의 재도전 결과예요.")
        show_past()
    else:
        show_past()
        show_answer_box()
        if result:
            show_result()
    show_failed_retries(no, last["score"])


def show_question_cards(pairs: list[tuple[str, str]]):
    for angle, question in pairs:
        with st.container(border=True):
            st.caption(f"{angle} 관점")
            st.markdown(question)
    if pairs:
        ai_note("AI가 만든 질문")


def current_precheck(items: list[dict]) -> dict:
    """지금 화면의 체크 · 메모 상태 (리포트 · 이어 하기용)."""
    n = range(len(items))
    return coach.precheck_state(
        items,
        [bool(state.get(f"pre_found_{i}")) for i in n],
        [bool(state.get(f"pre_missing_{i}")) for i in n],
        [str(state.get(f"pre_memo_{i}", "")) for i in n],
    )


OVERVIEW_COLORS = {"공통": "#AEB0B6", "헬스케어": "#38BDF8"}  # 회차 태그와 같은 계열 (그 밖 분야는 보라)


def show_overview():
    """점검하기 맨 위 종합 점검: 회차마다 최신 종합 점수를 분야 색으로 (공통 회색 · 헬스케어 하늘색 …).
    공통 면접은 일반 역량, 분야 면접은 분야 특수 질문을 점검하므로 둘 다 합격선을 넘도록 안내한다 (고정 문장 · 숫자는 앱 계산)."""
    rounds = coach.round_overview(past_reports())
    if state.get("evaluation"):
        totals = coach.total_scores(state.evaluation, state.retries)
        rounds[int(state.round)] = {"round": int(state.round), "field": coach.field_of(profile),
                                    "total": totals["latest"], "current": True}
    if not rounds:
        return
    st.subheader(":material/insights: 종합 점검 · 공통과 분야 면접")
    st.caption("공통 면접은 어느 회사에서나 묻는 일반 역량을, 분야 면접은 그 분야만의 특수 질문을 점검해요. "
               f"두 가지 모두 합격선({coach.PASS_TOTAL}점)을 넘으면 실제 면접에 고르게 대비할 수 있어요.")
    rows = sorted(rounds.values(), key=lambda r: r["round"])
    chart = pd.DataFrame({
        "회차": [f"{r['round']}회차" + (" · 현재" if r.get("current") else "") for r in rows],
        "분야": [r["field"] for r in rows],
        "최신 종합": [r["total"] for r in rows],
    })
    fields = list(dict.fromkeys(chart["분야"]))
    bars = alt.Chart(chart, height=260).mark_bar(size=48, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("회차:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("최신 종합:Q", scale=alt.Scale(domain=[0, coach.TOTAL_MAX]), title="최신 종합 (0~100)"),
        color=alt.Color("분야:N", scale=alt.Scale(domain=fields, range=[OVERVIEW_COLORS.get(f, "#8B5CF6") for f in fields]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["회차", "분야", "최신 종합"],
    )
    line = alt.Chart(pd.DataFrame({"y": [coach.PASS_TOTAL]})).mark_rule(strokeDash=[4, 4], strokeWidth=2, color="#00BF40").encode(y="y:Q")
    st.altair_chart(bars + line, width="stretch")
    st.caption(f"초록 점선: 합격선 {coach.PASS_TOTAL}점 · 점수는 그 회차 최신 종합(재도전 최고 점수 반영)이에요.")

    best = coach.best_by_kind(rows)
    common_col, field_col = st.columns(2)
    common_col.metric("공통 면접 최고", f"{best['common']}/{coach.TOTAL_MAX}" if best["common"] is not None else "아직 없음")
    field_col.metric("분야 면접 최고", f"{best['field']}/{coach.TOTAL_MAX}" if best["field"] is not None else "아직 없음",
                     help=" · ".join(f"{f} {s}점" for f, s in best["by_field"].items()) or None)
    # 진행도: 회차 수(분야별) · 질문 은행 대비 나온 질문 (점수만으로는 얼마나 넓게 연습했는지 안 보여서)
    st.markdown("**:material/timeline: 진행도**")
    counts = {}
    for r in rows:
        counts[r["field"]] = counts.get(r["field"], 0) + 1
    st.caption(f"진행한 회차 {len(rows)}번 · " + " · ".join(f"{f} {n}번" for f, n in counts.items()))
    asked = {q for r in past_reports() for q in r["questions"]} | {q["question"] for q in state.get("questions", [])}
    try:
        coverage = coach.question_coverage(coach.load_questions(), profile["job"], asked,
                                           [coach.DEFAULT_FIELD, *[f for f in counts if f != coach.DEFAULT_FIELD]])
    except (OSError, ValueError, KeyError):
        coverage = []
    for cov in coverage:
        label = "공통 질문" if cov["field"] == coach.DEFAULT_FIELD else f"{cov['field']} 질문"
        st.progress(cov["asked"] / cov["total"], text=f"{label} {cov['asked']}/{cov['total']}개 나옴 (질문 은행 기준)")
    st.caption("공통 질문은 분야와 상관없이 어느 면접에서나 나와요. 다 나온 뒤에는 '새 질문으로' 를 골라도 나온 질문이 다시 섞여요.")
    for kind, message in coach.overview_advice(best):
        getattr(st, kind)(message)
    st.divider()


def show_precheck():
    st.subheader(":material/search: 사전 정보 직접 탐색")
    st.write(
        "궁금하지만 면접 질문으로는 어울리지 않을 수 있는 정보예요. 면접 전에 스스로 찾아 채워 보세요. "
        "찾아봐도 없으면 **언제 확인하면 되는지** 알려 드려요."
    )
    try:
        items = coach.load_precheck()
    except (OSError, KeyError, ValueError):
        st.error("사전 탐색 체크리스트(data/사전탐색_체크리스트.csv)를 읽지 못했어요.")
        return

    found = [bool(state.get(f"pre_found_{i}")) for i in range(len(items))]
    missing = [bool(state.get(f"pre_missing_{i}")) for i in range(len(items))]
    summary = coach.precheck_summary(items, found, missing)
    st.progress(summary["found"] / summary["total"], text=f"찾음 {summary['found']}/{summary['total']} · 못 찾음 {summary['missing']}")

    groups = list(dict.fromkeys(item["group"] for item in items))
    for group in groups:
        with st.expander(group):
            for i, item in enumerate(items):
                if item["group"] != group:
                    continue
                with st.container(border=True):
                    st.checkbox(f":material/check_circle: **{item['item']}**", key=f"pre_found_{i}")
                    st.caption(f"찾는 곳: {item['where']}")
                    st.text_input(
                        "찾은 내용 메모",
                        key=f"pre_memo_{i}",
                        placeholder="예: 2025년 시리즈 B 투자",
                        label_visibility="collapsed",
                        max_chars=coach.MAX_MEMO_CHARS,
                    )
                    if st.checkbox(":material/help: 찾아봐도 없어요", key=f"pre_missing_{i}") and not state.get(f"pre_found_{i}"):
                        st.info(coach.PRECHECK_TIMING[item["timing"]])

    if summary["missing"]:
        st.markdown("**못 찾은 정보는 이렇게 챙기세요**")
        for timing, names in summary["later"].items():
            if names:
                st.markdown(f"- {coach.PRECHECK_LATER_LABEL[timing]}: " + " · ".join(names))
    st.caption("체크와 메모는 면접리포트.md 에 들어가고, 다음 회차에 리포트를 올리면 이어져요.")


def show_last_question():
    st.subheader("추천 질문")
    st.write("면접 마지막의 \"마지막으로 할 질문 있나요?\" 에 할 질문을 회사 · 직무 · 성장 관점으로 추천해 드려요.")
    if st.button("마지막 질문 생성하기", type="primary"):
        if state.last_suggest:
            st.info("추천 질문을 이미 만들었어요. 아래에서 확인해 주세요.")  # 같은 추천을 다시 부르지 않는다
        else:
            def store(raw):
                state.last_suggest = coach.summarize_last_suggest(raw)

            if call_ai("질문을 만들고 있어요...", coach.build_last_suggest(profile), LAST_SUGGEST_INPUT,
                       LAST_SUGGEST_SCHEMA, "last_suggest", store):
                st.rerun()
    if state.last_suggest:
        show_question_cards(state.last_suggest)

    st.divider()
    st.subheader("내 질문 다듬기")
    st.write("직접 쓴 질문을 회사 · 직무 · 성장 관점으로 다듬어 드려요.")
    my_question = st.text_area(
        "면접관에게 할 내 질문", height=100, key="last_question_input", max_chars=coach.MAX_LAST_QUESTION_CHARS
    )
    if st.button("질문 다듬기"):
        instructions = coach.build_last_question(profile)
        if not my_question.strip():
            st.info("면접관에게 할 질문을 적은 뒤 눌러 주세요.")
        elif not coach.is_prompt_ready(instructions):
            st.error("마지막 질문 프롬프트에 빈칸(___)이 있어요. prompts.py 의 LAST_QUESTION 글자 수를 채워 주세요.")
        else:
            def store(raw):
                state.last_question = coach.summarize_last_question(raw)

            if call_ai("질문을 다듬고 있어요...", instructions, my_question.strip(),
                       LAST_QUESTION_SCHEMA, "last_question", store):
                st.rerun()

    result = state.last_question
    if result:
        show_question_cards(result["questions"])
        if result["why"]:
            st.markdown(f"**원래 질문에서 빠진 것:** {result['why']}")


def user_now() -> datetime:
    """사용자 브라우저 시간대의 지금 시각. 배포 서버 시계는 UTC 라서 그대로 쓰지 않는다."""
    try:
        tz = ZoneInfo(st.context.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz)


def show_report_checklist():
    """단계 체크리스트: 탭 7개 순서 그대로, 하위 항목은 들여 써서 (표시만 · 고르는 건 coach.report_checklist).
    위쪽 진행 막대와 같은 목록이라 'n단계 중 n단계 완료' 숫자가 늘 같다."""
    rows = checklist_rows()

    def icon(done: bool) -> str:
        return ":green[:material/check_box:]" if done else ":gray[:material/check_box_outline_blank:]"

    with st.container(border=True):
        st.markdown(f"**:material/checklist: 단계 체크리스트** · {coach.checklist_summary(rows)}")
        st.caption("앱이 지금 기록으로 자동 표시해요. 탭 번호와 같은 순서이고, 마지막이 이 리포트예요. 하위 항목은 그 단계 안에서 할 수 있는 일이에요.")
        for r in rows:
            detail = f" :gray[({r['detail']})]" if r["detail"] else ""
            tag = " :gray[· 선택]" if r["optional"] else ""
            number = f"{r['step']}. " if r["step"] else ""  # 리포트는 탭이 아니라 번호 없음
            lines = [f"{icon(r['done'])} **{number}{r['item']}**{detail}{tag}"]
            lines += [
                f"{'&nbsp;' * 7}{icon(s['done'])} {s['item']}" + (f" :gray[({s['detail']})]" if s["detail"] else "")
                for s in r["sub"]
            ]
            st.markdown("  \n".join(lines))


def show_report(ev: dict):
    """리포트 창: 개인정보 안내 · 확인 체크 · 다운로드 · 마지막 업데이트를 맨 위에, 그 아래 단계 체크리스트 · 미리보기."""
    today = user_now().date()  # 파일 이름 · 리포트 날짜 모두 사용자 시간대 기준

    # 리포트 내용이 바뀐 때만 '마지막 업데이트' 시각을 새로 찍는다 (가장 최신 시각 하나만 남긴다).
    content = build_current_report(ev)
    if state.get("report_content") != content:
        state.report_content = content
        state.report_updated = user_now().strftime("%Y-%m-%d %H:%M")
    report = build_current_report(ev, state.report_updated)

    file_name = coach.report_file_name(profile["company"], profile["job"], state.round, today)
    st.warning(
        ":material/lock: 리포트에는 이름 · 회사 · 내 경험 원문 · 면접 대화 · 답변 · 체크리스트 메모가 들어가요. "
        "다른 사람과 공유할 때 주의해 주세요."
    )
    # 위 안내를 확인했다고 체크해야 다운로드할 수 있다 (사용자 요청 — CLAUDE.md '버튼을 disabled 로 막지 말 것' 의 예외)
    agreed = st.checkbox("위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.", key="report_agree")
    button_col, time_col = st.columns([3, 2], vertical_alignment="center")
    button_col.download_button(
        f"{file_name} 다운로드",
        data=report,
        file_name=file_name,
        mime="text/markdown",
        type="primary",
        disabled=not agreed,
        on_click=mark_report_downloaded,  # 받으면 마지막 단계 완료 → 설문 안내
    )
    time_col.caption(f":material/schedule: 마지막 업데이트: **{state.report_updated}**")
    if not agreed:
        # 비활성 버튼이 왜 꺼져 있는지 알려 준다 (ui-ux-pro-max: Interaction · Disabled States)
        st.caption(":material/info: 위 안내를 확인하고 체크하면 다운로드 버튼이 켜져요.")
    show_report_checklist()
    st.caption(
        "오른쪽 위 복사 아이콘으로 내용을 복사할 수 있어요. 점수는 모두 앱이 계산한 값이고, "
        "'AI 의견' 표시가 붙은 글은 AI가 쓴 거예요. 마지막 질문을 만들어 두면 리포트에 같이 들어가요. "
        "다음 면접 시작 화면에서 이 파일을 올리면 이어서 할 수 있어요 (맨 끝 주석은 이어 하기용 데이터예요)."
    )
    st.code(report, language="markdown", wrap_lines=True)  # 긴 줄은 자동 줄바꿈 (가로 스크롤 없음)


# ── 최종 판결: 문자 → 이메일 연출. 판정은 coach.verdict(), 글은 모두 고정 문구 (AI 호출 없음) ──
VERDICT_CSS = """<style>
.vd { display: grid; gap: 14px; width: 100%; margin: 4px 0; overflow-wrap: anywhere; }
.vd * { box-sizing: border-box; }
.vd-phone { background: #171719; border-radius: 28px; padding: 18px 18px 22px;
  width: 100%; margin: 0; border: 4px solid #2E2F33; animation: vd-in .3s ease-out both; }
.vd-notch { width: 80px; height: 6px; border-radius: 3px; background: #2E2F33; margin: 0 auto 10px; }
.vd-contact { text-align: center; color: #F7F7F8; font-size: .875rem; font-weight: 600;
  border-bottom: 1px solid #2E2F33; padding-bottom: 8px; }
.vd-contact span { display: block; color: #AEB0B6; font-size: .75rem; font-weight: 400; }
/* 문자 대화: 아래에서부터 쌓인다. 새 문자가 아래에 자라면 앞 문자가 위로 밀려 올라간다 */
.vd-thread { display: flex; flex-direction: column; justify-content: flex-end; min-height: 190px; padding-top: 10px; }
.vd-sms { background: #2E2F33; color: #F7F7F8; border-radius: 14px 14px 14px 4px; padding: 10px 13px;
  font-size: .92em; line-height: 1.5; max-width: 75%; width: fit-content; overflow: hidden; }
.vd-time { color: #878A93; font-size: .75rem; margin: 3px 0 0 4px; }
.vd-m1 { animation: vd-pop .2s ease-out .5s both; }
.vd-m2 { overflow: hidden; animation: vd-grow .3s ease-out 1.9s both; }
/* 결과 메일: 메일 앱 한 통처럼 (머리글 · 제목 · 결과 카드 · 점수 3칸 · 서명 · 안내 주석) */
.vd-mail { background: #FFFFFF; color: #171719; border: 1px solid #E1E2E4; border-radius: 16px; overflow: hidden;
  line-height: 1.6; word-break: keep-all; box-shadow: 0 1px 2px rgba(23, 23, 25, .04); animation: vd-in .3s ease-out 3s both; }
.vd-mail-bar { display: flex; align-items: center; gap: 8px; padding: 10px 24px; background: #F7F7F8;
  border-bottom: 1px solid #EAEBEC; color: #70737C; font-size: .8125rem; }
.vd-dot { width: 8px; height: 8px; border-radius: 4px; background: #10256B; }
.vd-mail-head { display: flex; align-items: center; gap: 12px; padding: 20px 24px 0; }
.vd-avatar { flex: 0 0 40px; height: 40px; border-radius: 20px; background: #10256B; color: #FFFFFF;
  display: grid; place-items: center; font-weight: 600; }
.vd-sender { flex: 1; min-width: 0; line-height: 1.4; }
.vd-sender b { display: block; font-weight: 600; font-size: .9375rem; }
.vd-sender span, .vd-when { color: #70737C; font-size: .8125rem; }
.vd-subject { padding: 16px 24px 0; font-size: 1.25rem; font-weight: 600; line-height: 1.35; word-break: keep-all; }
.vd-body { padding: 16px 24px 24px; }
.vd-body > p { margin: 0 0 16px; }
.vd-status { border: 1px solid; border-radius: 12px; padding: 16px 18px; margin-bottom: 16px; }
.vd-status.pass { background: #F2FFF6; border-color: #B8EFCA; }
.vd-status.candidate { background: #F3F5FB; border-color: #CDD5EE; }
.vd-status.more { background: #FFF5F5; border-color: #F8CFCF; }
.vd-pill { display: inline-block; font-size: .75rem; font-weight: 600; color: #FFFFFF; border-radius: 999px;
  padding: 2px 10px; margin-bottom: 8px; }
.pass .vd-pill { background: #006E25; } .candidate .vd-pill { background: #10256B; } .more .vd-pill { background: #B00C0C; }
.vd-result { font-size: 1.125rem; font-weight: 600; line-height: 1.4; margin-bottom: 6px; word-break: keep-all; }
.pass .vd-result { color: #006E25; } .candidate .vd-result { color: #10256B; } .more .vd-result { color: #B00C0C; }
.vd-status p { margin: 0; color: #46474C; }
.vd-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 20px; }
.vd-stat { border: 1px solid #EAEBEC; border-radius: 12px; padding: 12px 14px; }
.vd-stat.key { background: #F7F7F8; }
.vd-stat span { display: block; color: #70737C; font-size: .8125rem; }
.vd-stat b { font-size: 1.375rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.vd-stat small { color: #70737C; font-size: .8125rem; }
.vd-sign { color: #46474C; }
.vd-tip { border: 1px solid #CDD5EE; background: #F3F5FB; border-radius: 12px; padding: 14px 18px; margin-bottom: 20px; }
.vd-tip b { color: #10256B; font-weight: 600; }
.vd-tip p { margin: 4px 0 0; color: #46474C; }
.vd-foot { background: #F7F7F8; border-top: 1px solid #EAEBEC; padding: 14px 24px; color: #70737C; font-size: .75rem; }
.vd-foot p { margin: 0; }
@keyframes vd-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes vd-pop { from { opacity: 0; transform: translateY(10px) scale(.96); } to { opacity: 1; transform: none; } }
@keyframes vd-grow { from { opacity: 0; max-height: 0; margin-top: 0; transform: translateY(12px); }
  to { opacity: 1; max-height: 260px; margin-top: 10px; transform: none; } }
@media (prefers-reduced-motion: reduce) { .vd-phone, .vd-m1, .vd-m2, .vd-mail { animation: none; } }
</style>"""


def show_verdict(ev: dict):
    totals = coach.total_scores(ev, state.retries)
    result = coach.verdict(totals, ev["panel_average"])
    st.caption(
        f"판정 기준: **합격** 위원 평균 {coach.PASS_PANEL:.1f} · 최신 종합 {coach.PASS_TOTAL} 이상 · "
        f"**합격 후보** 위원 평균 {coach.CANDIDATE_PANEL:.1f} · 최신 종합 {coach.CANDIDATE_TOTAL} 이상 · "
        "그 밖은 재도전 필요. 재도전하면 최신 종합이 바뀌어요 (평가 탭 타이틀과 같은 기준)."
    )
    if not state.verdict_open:
        if st.button(":material/mail: 모의 결과 확인하기", type="primary"):
            state.verdict_open = True
            st.rerun()
        return

    company = html.escape(profile["company"])
    name = html.escape(profile["name"])
    job = html.escape(profile["job"])
    need = " · ".join(html.escape(s) for s in result["short"])
    # 위원 평균이 모자라면 재도전만으로는 못 채운다 (재도전은 종합 점수만 올림) → 다음 회차 면접을 안내
    next_round = f"재도전으로 대답을 수정하는 연습을 거친 후, {int(state.round) + 1}회차 면접을 통해 위원 평가 점수를 올려보세요."
    if result["level"] == "pass":
        title, body = "모의면접 합격입니다. 당신의 가능성을 증명했습니다.", "암기와 말하기 연습을 지속하세요."
    elif result["level"] == "candidate":
        title = "합격 후보로 선정되었습니다."
        body = (f"합격선(위원 평균 {coach.PASS_PANEL:.1f} · 종합 {coach.PASS_TOTAL})까지 <b>{need}</b> 남았어요. "
                + (next_round if result["panel_short"] else
                   "경쟁률이 높을 경우 재도전으로 대답을 수정하거나 암기와 말하기 연습으로 다듬어보세요."))
    else:
        title = next_round if result["panel_short"] else "재도전으로 대답을 수정해보세요."
        body = f"합격 후보까지 <b>{need}</b> 부족해요. 아직 역전의 기회가 남아 있어요."
    initial = html.escape(profile["company"].strip()[:1] or "M")
    # 공통 분야로 본 면접이면: 지원할 회사의 분야를 골라 다음 회차를 해 보도록 추천 (고정 문장)
    is_common = coach.field_of(profile) == coach.DEFAULT_FIELD
    tip = (
        '<div class="vd-tip"><b>다음 회차 추천 · 분야를 골라 면접 보기</b>'
        f"<p>이번 면접은 <b>공통</b> 분야로 진행했어요. 다음 회차에서 지원할 회사의 분야"
        f"({html.escape(field_examples())})를 고르면, 그 분야 질문과 평가 관점으로 실제 면접에 더 가깝게 준비할 수 있어요.</p></div>"
        if is_common else ""
    )  # 보낸 사람 동그라미: 회사 이름 첫 글자
    mail = (
        '<div class="vd-mail">'
        + '<div class="vd-mail-bar"><span class="vd-dot"></span>받은편지함 · 새 메일 1통</div>'
        + f'<div class="vd-mail-head"><div class="vd-avatar">{initial}</div>'
        + f'<div class="vd-sender"><b>{company} 모의면접 위원회</b><span>받는 사람: {name}</span></div>'
        + '<div class="vd-when">지금</div></div>'
        + f'<div class="vd-subject">[{company}] {job} 신입 모의면접 결과 안내 ({state.round}회차)</div>'
        + '<div class="vd-body">'
        + f"<p>{name}님, 모의면접에 참여해 주셔서 감사합니다.</p>"
        + f'<div class="vd-status {result["level"]}"><span class="vd-pill">{result["label"]}</span>'
        + f'<div class="vd-result">{title}</div><p>{body}</p></div>'
        + '<div class="vd-stats">'
        + f'<div class="vd-stat key"><span>최신 종합</span><b>{totals["latest"]}</b><small>/{coach.TOTAL_MAX}</small></div>'
        + f'<div class="vd-stat"><span>최초 종합</span><b>{totals["first"]}</b><small>/{coach.TOTAL_MAX}</small></div>'
        + f'<div class="vd-stat"><span>위원 평균</span><b>{ev["panel_average"]:.1f}</b><small>/{coach.PANEL_MAX}</small></div>'
        + "</div>"
        + tip
        + f'<div class="vd-sign">{company} 모의면접 위원회 드림</div>'
        + "</div>"
        # 안내 문구는 메일 맨 아래 주석으로 모은다
        + '<div class="vd-foot">'
        + f"<p>※ 보낸 사람: {company} 모의면접 위원회 · 이 앱에서만 보이는 시뮬레이션이에요.</p>"
        + "<p>※ 이 결과는 AI 모의면접 학습 지표이며 실제 채용 결과와 무관하고, 실제 합격 가능성을 보장하지 않아요. "
          "문자와 메일은 실제로 보내지 않아요.</p>"
        + "</div></div>"
    )
    st.html(
        VERDICT_CSS
        + '<div class="vd">'
        + '<div class="vd-phone"><div class="vd-notch"></div>'
        + f'<div class="vd-contact">{company} (모의)<span>문자 메시지</span></div>'
        + '<div class="vd-thread">'
        + '<div class="vd-m1"><div class="vd-sms">최종 면접 결과가 도착했습니다.</div><div class="vd-time">지금</div></div>'
        + f'<div class="vd-m2"><div class="vd-sms">{name}님, {company} {job} 신입 모의면접 결과를 '
          "메일로 보내 드렸습니다. 메일함을 확인해 주세요.</div><div class=\"vd-time\">지금</div></div>"
        + "</div></div>"
        + mail
        + "</div>"
    )
    if is_common and st.button(f":material/explore: 분야를 골라 {coach.next_round({'round': state.round})}회차 면접 진행하기",
                               width="stretch", key="verdict_pick_field",
                               help="다음 회차 안내 창을 열어요. 시작 화면에서 지원할 회사의 분야를 고를 수 있어요."):
        state.open_next_round = True
        st.rerun()
    # 왼쪽 재도전 · 오른쪽 성장 리포트 (둘 다 같은 보통 버튼). 합격이면 재도전 칸 없이 리포트가 왼쪽에.
    first_col, second_col = st.columns(2)
    if not result["passed"] and first_col.button(":material/replay: 재도전으로 점수 올리기", width="stretch"):
        state.go_tab = RETRY_TAB
        st.rerun()
    report_col = first_col if result["passed"] else second_col
    if report_col.button(":material/description: 성장 리포트 보기", width="stretch"):
        state.go_tab = LAST_TAB  # 점검하기 탭 맨 위의 종합 점검(공통 · 분야 비교)으로
        st.rerun()


# ── 암기 시뮬레이션: 핵심어 뽑기 · 빈칸 · 채점은 모두 coach.py 규칙 (AI 호출 없음) ──
WEEKDAYS = "월화수목금토일"
MEMO_CSS = f"""<style>
.mm {{ line-height: 2.1; overflow-wrap: anywhere; }}
.mm .key {{ color: {HIGHLIGHT_TEXT}; background: #E8EBF5; border-radius: 4px; padding: 1px 6px; margin: 0 3px 3px 0;
  display: inline-block; font-size: .92em; }}
.mm .blank {{ color: transparent; border-bottom: 2px solid currentColor; border-bottom-color: #AEB0B6; padding: 0 2px; }}
.mm .shown {{ color: {HIGHLIGHT_TEXT}; background: #DCE1F0; border-radius: 3px; padding: 0 2px; }}
.mm .kw {{ color: {HIGHLIGHT_TEXT}; background: #E8EBF5; border-radius: 3px; padding: 0 3px; font-weight: 600; }}
.mm .rest {{ opacity: .62; }}  /* 테마 글자색을 흐리게: 라이트 · 다크 모두 대비 4.5 이상 */
.mm .badge {{ display: inline-block; font-size: .75em; font-weight: 600; color: #B00C0C; background: #FFFFFF;
  border: 1px solid #FF4242; border-radius: 4px; padding: 0 4px; margin-right: 4px; line-height: 1.4; }}
.mm .sline {{ padding: 2px 6px; margin-bottom: 4px; }}
.mm .sgap {{ color: {HIGHLIGHT_TEXT}; background: #FEECEC; border-left: 4px solid #FF4242; border-radius: 4px;
  padding: 2px 6px; margin-bottom: 4px; }}
.mm .legend .sgap {{ display: inline; padding: 0 4px; border-left-width: 3px; }}
.mm .legend {{ font-size: .85em; }}
</style>"""


# 말하기 중 경과 시간 표시 (브라우저에서 1초마다). __ELAPSED__ = 서버가 잰 경과(ms), __START__ = 시작 시각.
# 네이비(#4263D6)는 밝은 · 어두운 화면 모두에서 읽힌다.
SPEAK_TIMER_HTML = """<div id="t" style="font:600 1.2rem system-ui,sans-serif;color:#4263D6"></div>
<script>
const s = Date.now() - __ELAPSED__;
const el = document.getElementById("t");
function tick() {
  const e = Math.floor((Date.now() - s) / 1000);
  el.textContent = "● 말하는 중 · 시작 __START__ · "
    + String(Math.floor(e / 60)).padStart(2, "0") + ":" + String(e % 60).padStart(2, "0");
}
tick(); setInterval(tick, 250);
</script>"""


def latest_answer(no: int) -> str:
    """재도전했으면 마지막 재도전 답, 아니면 면접 때 답."""
    retry = state.retries.get(no)
    return retry["answer"] if retry else coach.answer_text(state.messages, no - 1)


def key_chips(keys: list[str], css: str = "key") -> str:
    return "".join(f'<span class="{css}">{html.escape(k)}</span>' for k in keys) or "<small>(핵심어 없음)</small>"


def go_memo_step(index: int):
    """단계별 연습: MEMO_STEPS[index] 로 옮긴다 (모드 · 빈칸 단계는 다음 실행에서 그리기 전에 정한다)."""
    state.go_memo = index
    st.rerun()


def timer_buttons(key: str, phase: str):
    """한 단계의 타이머 버튼. 재는 중에는 ':material/play_arrow: 시작' 자리가 ':material/close: 취소'(기록하지 않고 끝내기)로 바뀐다.
    ':material/stop: 완료' 는 기록하고 끝낸다. 시작 · 완료 시각과 걸린 시간은 서버 시각으로 잰다."""
    timer = state.get("speak_timer")
    running = bool(timer) and timer["key"] == key and timer["phase"] == phase
    start_col, stop_col = st.columns(2)
    if running:
        # 시작과 취소는 다른 key 라서, 시작을 누른 다음 실행에서 취소가 눌린 것으로 잡히지 않는다
        if start_col.button(":material/close: 취소", key=f"speak_cancel_{phase}_{key}", width="stretch",
                            help="기록하지 않고 타이머를 끝내요."):
            state.speak_timer = None
            st.rerun()
    elif start_col.button(":material/play_arrow: 시작", key=f"speak_start_{phase}_{key}", width="stretch", type="primary"):
        state.speak_timer = {"key": key, "phase": phase, "t": time.time(), "label": user_now().strftime("%H:%M:%S")}
        st.rerun()
    if stop_col.button(":material/stop: 완료", key=f"speak_stop_{phase}_{key}", width="stretch",
                       type="primary" if running else "secondary", help="걸린 시간을 기록하고 끝내요."):
        if not running:
            st.info("먼저 이 단계의 ':material/play_arrow: 시작' 을 눌러 주세요.")
        else:
            log = {
                "시작": timer["label"],
                "완료": user_now().strftime("%H:%M:%S"),
                "걸린 시간(초)": round(time.time() - timer["t"]),
            }
            logs = speak_logs_for(key)
            logs[phase] = ([log] + logs.get(phase, []))[: coach.SPEAK_LOG_KEEP]
            state.speak_logs[key] = logs
            state.speak_timer = None
            st.rerun()
    if running:
        # 서버 기준 경과를 넘겨서 브라우저 시계와 서버 시계가 달라도 같은 시간을 보여 준다.
        # st.iframe 은 스크립트를 실행하므로 사용자 글 · AI 출력은 넣지 않는다 (숫자와 서버 시각만 넣음).
        elapsed_ms = int((time.time() - timer["t"]) * 1000)
        st.iframe(
            SPEAK_TIMER_HTML.replace("__ELAPSED__", str(elapsed_ms)).replace("__START__", timer["label"]),
            height=40,
        )
    return running


def skeleton_html(text: str) -> str:
    """뼈대: 문장마다 핵심어 칩."""
    parts = [f'<div>{i}. {key_chips(item["keys"])}</div>' for i, item in enumerate(coach.skeleton(text), 1)]
    return MEMO_CSS + '<div class="mm">' + "".join(parts) + "</div>"


def cloze_html(text: str, level: int, reveal: bool = False) -> str:
    """빈칸: 가린 핵심어는 밑줄만 (reveal 이면 노랗게 보여 줌)."""
    words = []
    for word, hidden in coach.cloze(text, level):
        css = ("shown" if reveal else "blank") if hidden else ""
        words.append(f'<span class="{css}">{html.escape(word)}</span>' if css else html.escape(word))
    return MEMO_CSS + '<div class="mm">' + " ".join(words) + "</div>"


def go_speak_phase(phase: str):
    """말하기 모드: 그 단계(· 힌트)로 옮긴다 (다음 실행에서 그리기 전에 정한다)."""
    state.go_speak = phase
    st.rerun()


def speak_logs_for(key: str) -> dict:
    logs = state.speak_logs.get(key, {})
    if isinstance(logs, list):  # 단계가 나뉘기 전 기록은 '대본 없이 말하기' 로 본다
        logs = {"speak": logs}
    return logs


def show_speaking(key: str, text: str, question: str):
    """:material/record_voice_over: 말하기 모드: 1단계 대본 읽기 → 2단계 힌트(뼈대 → 빈칸 가볍게 · 절반 · 전부) → 3단계 대본 없이.
    단계마다 타이머로 재고, 1단계 읽기 시간과 비교한다."""
    if state.get("speak_step") not in coach.SPEAK_STEP_NAMES:
        state.speak_step = 1
    step = st.segmented_control(
        "단계", list(coach.SPEAK_STEP_NAMES), key="speak_step", required=True,
        format_func=lambda n: f"{SPEAK_STEP_ICONS[n]} {coach.SPEAK_STEP_NAMES[n]}", width="stretch",
    )

    hint = None
    if step == 1:
        st.caption("대본을 소리 내어 읽으며 재요. 내 읽기 속도를 구하고, 2 · 3단계 시간과 비교해요.")
    elif step == 2:
        if state.get("speak_hint") not in coach.SPEAK_HINTS:
            state.speak_hint = "skeleton"
        hint = st.segmented_control(
            "힌트", list(coach.SPEAK_HINTS), key="speak_hint", required=True, format_func=coach.SPEAK_HINTS.get,
            help="뼈대 → 가볍게 → 절반 → 전부 순서로 힌트를 줄여 가며 말해 보세요.",
        )
        st.caption("아래 힌트만 보고 소리 내어 말하며 재요.")
    else:
        st.caption("대본을 가리고 기억나는 대로 말하며 재요.")
    phase = coach.speak_phase(step, hint)

    running = timer_buttons(key, phase)
    if step == 1:
        if running:
            with st.container(border=True):
                st.write(text)
        else:
            st.caption(":material/play_arrow: 시작을 누르면 대본이 보여요.")
    elif step == 2:
        st.html(skeleton_html(text) if hint == "skeleton" else cloze_html(text, hint))

    logs = speak_logs_for(key)
    read_s = logs["read"][0]["걸린 시간(초)"] if logs.get("read") else None
    if logs.get(phase):
        for kind, message in coach.phase_feedback(read_s, logs[phase][0]["걸린 시간(초)"], phase, text, question):
            getattr(st, kind)(message)

    # 지금까지 잰 단계별 최근 시간 (1단계 읽기 대비)
    progress = []
    for p in coach.SPEAK_PHASES:
        if logs.get(p):
            seconds = logs[p][0]["걸린 시간(초)"]
            versus = f"{(seconds - read_s) / read_s * 100:+.0f}%" if read_s and p != "read" else "-"
            progress.append({"단계": coach.phase_label(p), "최근 시간(초)": seconds, "읽기 대비": versus})
    if progress:
        st.markdown("**단계별 기록**")
        st.table(progress, hide_index=True)

    following = coach.next_phase(phase)
    if following and st.button(f"다음 단계로 :material/arrow_forward: {coach.phase_label(following)}", key=f"speak_next_{phase}"):
        go_speak_phase(following)


def show_memo_strategy():
    try:
        st.markdown(coach.load_memo_strategy())
    except OSError:
        st.error("암기 전략 문서(data/암기전략.md)를 읽지 못했어요.")
    st.markdown("**복습 일정**")
    for label, day in coach.review_schedule(user_now().date()):
        st.markdown(f"- {label}: {day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})")


def show_memo_skeleton(no: int, source: str, text: str):
    st.caption(":material/record_voice_over: 핵심어만 보고 소리 내어 답해 보세요. 걸리는 시간은 위 '내 대본' 옆에 있어요.")
    # 스위치: 끄면 뼈대(핵심어)만, 켜면 전체 문장에서 빠진 내용을 회색으로 함께
    full = st.toggle(
        "전체 문장 함께 보기", key=f"memo_full_{no}_{source}",
        help="끄면 뼈대(핵심어)만 보여요. 켜면 핵심어 사이에 빠진 내용을 회색으로 함께 보여 줘요.",
    )
    if full:
        rows = []
        for i, sentence in enumerate(coach.split_sentences(text), 1):
            words = [
                f'<span class="{"kw" if kind == "key" else "rest"}">{html.escape(w)}</span>'
                for w, kind in coach.mark_words(sentence)
            ]
            rows.append(f"<div>{i}. {' '.join(words)}</div>")
        st.html(MEMO_CSS + '<div class="mm">' + "".join(rows)
                + '<div class="legend"><span class="kw">핵심어</span> · <span class="rest">회색은 빠진 내용</span></div></div>')
    else:
        st.html(skeleton_html(text))


def show_memo_cloze(no: int, source: str, text: str) -> int:
    if state.get("memo_level") not in coach.MEMO_TAGS:
        state.memo_level = 1  # 태그는 하나가 꼭 골라져 있게 (기본: 가볍게)
    level = st.segmented_control(
        "가리는 양", options=list(coach.MEMO_TAGS), key="memo_level", required=True,
        format_func=coach.MEMO_TAGS.get,
        help="가볍게: 핵심어 4개 중 1개 · 절반: 2개 중 1개 · 전부: 핵심어를 모두 가려요.",
    )
    reveal = st.toggle("정답 보기", key=f"memo_reveal_{no}_{source}_{level}")
    st.html(cloze_html(text, level, reveal))
    hidden_count = sum(1 for _, h in coach.cloze(text, level) if h)
    st.caption(f"빈칸 {hidden_count}개 · 빈칸에 들어갈 말을 소리 내어 말한 뒤 '정답 보기' 로 확인해 보세요.")
    return level


def sentence_lines(rows: list[str]) -> str:
    return MEMO_CSS + '<div class="mm">' + "".join(rows) + "</div>"


def show_memo_simulation(result_key: str, question: dict, text: str):
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        st.markdown(question["question"])
    attempt = st.text_area(
        "기억나는 대로 답해 보세요 (원래 답은 가려져 있어요)", height=160,
        key=f"memo_try_{result_key}", max_chars=coach.MAX_ANSWER_CHARS,
    )
    if st.button("확인하기", type="primary", key=f"memo_check_{result_key}"):
        if not attempt.strip():
            st.info("기억나는 대로 적은 뒤 눌러 주세요.")
        else:
            check = {
                **coach.recall_check(text, attempt),
                "sentences": coach.sentence_recall(text, attempt),
                "attempt": attempt.strip(),
            }
            state.memo_results[result_key] = check
            state.memo_best[result_key] = max(state.memo_best.get(result_key, 0), check["recall"])
    check = state.memo_results.get(result_key)
    if not check:
        return

    written = check.get("attempt", attempt)  # 이 칸이 생기기 전 기록은 지금 칸의 글
    sentences = check.get("sentences") or coach.sentence_recall(text, written)
    judged = [row for row in sentences if row["remembered"] is not None]
    remembered = sum(1 for row in judged if row["remembered"])
    rate_col, sentence_col, best_col = st.columns(3)
    rate_col.metric("핵심어 기억", f"{check['recall']}%", help=f"{len(check['found'])}/{check['total']}개")
    sentence_col.metric("문장 기억", f"{remembered}/{len(judged)}")
    best_col.metric("이 답 최고 기록", f"{state.memo_best.get(result_key, 0)}%")
    st.progress(check["recall"] / 100)
    back = coach.fallback_step(check["recall"])
    if back is None:
        st.success(f"핵심어를 {coach.MEMO_PASS}% 넘게 기억했어요. 다음 질문으로 넘어가도 좋아요.")
    else:
        # 생각보다 덜 외워졌으면 낮은 단계부터 다시
        st.warning(
            f"생각보다 덜 외워졌어요 ({check['recall']}%). "
            f"**{coach.step_label(back)}** 부터 다시 연습하고 돌아오세요."
        )
        if st.button(f":material/fast_rewind: {coach.step_label(back)} 부터 다시", key=f"memo_back_{result_key}", type="primary"):
            go_memo_step(back)

    # 원래 답(왼쪽) · 내가 쓴 답(오른쪽)을 문장마다 한 줄씩 나란히. 기억 못 한 원래 문장만 칠한다.
    left, right = st.columns(2)
    with left:
        st.markdown("**원래 답**")
        st.html(sentence_lines([
            # 색만으로 구분하지 않도록 '놓침' 글자 배지도 붙인다 (ui-ux-pro-max: Color Only)
            (f'<div class="sgap"><span class="badge">놓침</span>{i}. {html.escape(row["sentence"])}</div>'
             if row["remembered"] is False else f'<div class="sline">{i}. {html.escape(row["sentence"])}</div>')
            for i, row in enumerate(sentences, 1)
        ]))
    with right:
        st.markdown("**내가 쓴 답**")
        st.html(sentence_lines([
            f'<div class="sline">{i}. {html.escape(s)}</div>' for i, s in enumerate(coach.split_sentences(written), 1)
        ]))
    st.html(MEMO_CSS + f'<div class="mm"><div class="legend"><span class="sgap">칠한 문장</span> = 그 문장 핵심어를 '
            f"{round(coach.SENTENCE_RECALL * 100)}% 미만으로 쓴 원래 문장</div></div>")


TEXT_MODE, SPEAK_MODE = ":material/edit_note: 텍스트 모드", ":material/record_voice_over: 말하기 모드"


def script_hidden() -> bool:
    """외우는 중이라 대본을 가려야 하는 단계: 텍스트 ③ 실전 시뮬레이션 · 말하기 모드 (말하기 1단계는 시작하면 대본이 나온다)."""
    if state.get("memo_top") == SPEAK_MODE:
        return True
    return state.get("memo_view") == coach.MEMO_MODES[-1]


def show_script_editor(no, result_key: str, original: str, text: str, ev: dict | None, practice: dict | None = None):
    """:material/menu_book: 대본: 먼저 읽고, 아래 '넓게 열어 고치기' 로 고친다. 저장하면 모든 연습 단계가 고친 대본을 쓴다.
    화면 폭이 좁아서 넓은 창(대화 상자)에서 원래 대본 | 고친 대본을 나란히 보며 고친다.
    외우는 단계(script_hidden)에서는 대본을 접어 둔다."""
    edited = result_key in state.memo_edits
    st.markdown(":material/menu_book: **내 대본**" + (" · :green[고친 대본]" if edited else "")
                + f"  :gray[· 소리 내어 읽으면 약 {coach.speak_seconds(text)}초]")
    lines = "  \n".join(coach.split_sentences(text)) or ":gray[아직 대본이 없어요. 아래 버튼으로 써 보세요.]"
    if script_hidden():
        with st.expander("대본 펼쳐 보기 · 지금은 외우는 단계라 접어 뒀어요"):
            st.markdown(lines)
    else:
        with st.container(border=True):
            st.markdown(lines)
    label = ":material/open_in_full: 넓게 열어 고치기" if text else ":material/edit: 넓게 열어 대본 쓰기"
    if st.button(label, key=f"memo_edit_open_{result_key}",
                 help="원래 대본과 고친 대본을 나란히 보며 고쳐요. 말해 보니 어색한 곳이 있으면 바로 고쳐 보세요."):
        script_dialog(no, result_key, original, text, ev, practice)
    if not practice:  # 다른 질문은 연습만: 재도전 검토 내역이 없다
        show_review_result(no, result_key, ev)


def graded_answers(no: int) -> set[str]:
    """이 질문에서 이미 채점받은 답 (면접 때 답 · 재도전한 답). 띄어쓰기 · 줄바꿈 차이는 같은 답으로 본다."""
    def norm(s: str) -> str:
        return " ".join(s.split())
    answers = [coach.answer_text(state.messages, no - 1)] + [a["answer"] for a in state.get("retry_history", {}).get(no, [])]
    return {norm(a) for a in answers if a.strip()}


@st.dialog("대본 고치기", width="large")
def script_dialog(no, result_key: str, original: str, text: str, ev: dict | None, practice: dict | None = None):
    """원래 대본 | 고친 대본. '수정하고 재도전 검토 받기' 는 재도전 탭과 같은 RETRY 채점 · 같은 횟수 상한 (AI 1번).
    이미 채점받은 대본과 같으면 다시 채점하지 않는다 (AI 점수가 흔들려 점수만 바뀌고 기회가 줄기 때문).
    practice ({question, label}): 이번 회차가 아닌 '다른 질문' — 저장 · 되돌리기만 있고 채점하지 않는다."""
    draft_key = f"memo_draft_{result_key}"
    # 저장하지 않고 창을 닫아도 쓰던 글은 남긴다 (창이 닫히면 칸의 값은 지워지므로 따로 보관)
    kept = state.setdefault("memo_draft_kept", {})
    by_line = "\n".join(coach.split_sentences(text))  # 왼쪽 원래 대본처럼 한 문장씩 줄을 바꿔 비교하기 쉽게
    if state.pop("memo_draft_reset", None) == result_key:
        kept.pop(result_key, None)
        state[draft_key] = by_line  # 칸을 그리기 전에만 값을 바꿀 수 있다
    elif draft_key not in state:
        state[draft_key] = kept.get(result_key, by_line)

    def keep_draft():
        kept[result_key] = state[draft_key]

    if practice:
        st.markdown(f"**다른 질문 연습** {practice['question']}")
    else:
        st.markdown(f"**질문 {no}.** {state.questions[no - 1]['question']}")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**원래 대본** · {practice['label'] if practice else current_answer_label()}")
        with st.container(border=True, height=360):
            st.markdown("  \n".join(coach.split_sentences(original)) or "(답 없음)")
    with right:
        draft = st.text_area("**고친 대본**", key=draft_key, height=360, max_chars=coach.MAX_ANSWER_CHARS, on_change=keep_draft)
        if result_key in kept and " ".join(kept[result_key].split()) != " ".join(text.split()):
            st.caption(":material/draft: 저장하지 않은 고친 글이에요. 창을 닫아도 남아 있어요.")
    save_col, review_col, undo_col = st.columns([1, 1.4, 1])
    if save_col.button(":material/save: 고친 대본 저장", key=f"memo_save_{result_key}", width="stretch"):
        if not draft.strip():
            st.info("대본을 적은 뒤 저장해 주세요.")
        else:
            state.memo_edits[result_key] = draft.strip()
            state.memo_results.pop(result_key, None)  # 대본이 바뀌었으니 지난 채점은 지운다
            kept.pop(result_key, None)
            st.rerun()
    if practice:
        review_col.caption("다른 질문은 연습만 해요. 점수는 이번 회차 면접 답으로만 계산해요.")
    elif review_col.button(":material/replay: 수정하고 재도전 검토 받기", key=f"memo_review_{result_key}", type="primary", width="stretch"):
        used = state.retry_counts.get(no, 0)
        if not draft.strip():
            st.info("대본을 적은 뒤 눌러 주세요.")
        elif not ev:
            st.info("위원 4명에게 평가받은 뒤에 재도전 검토를 받을 수 있어요. :material/forum: 면접 탭의 '위원 4명에게 평가받기' 를 눌러 주세요.")
        elif used >= coach.MAX_RETRIES:
            st.info(f"이 질문은 재도전 검토를 {coach.MAX_RETRIES}번 모두 받았어요. 고친 대본은 저장해서 연습할 수 있어요.")
        elif " ".join(draft.split()) in graded_answers(no):
            st.info("이미 채점받은 대본이라 다시 채점하지 않았어요 (재도전 기회는 그대로예요). "
                    "대본을 고친 뒤 다시 누르거나, 연습만 하려면 '고친 대본 저장' 을 눌러 주세요.")
        else:
            last = ev["answers"][no - 1]
            new_answer = draft.strip()

            def store(raw):
                state.memo_edits[result_key] = new_answer
                attempt = {"answer": new_answer, **coach.summarize_retry(raw)}
                record_retry(no, attempt, last["score"])
                state.retry_counts[no] = used + 1
                state.memo_results.pop(result_key, None)
                state.memo_reviews[result_key] = len(state.retry_history[no]) - 1  # 몇 번째 재도전인지
                kept.pop(result_key, None)

            if call_ai(
                "고친 대본을 채점하고 있어요...",
                coach.build_retry(profile, state.questions[no - 1], coach.answer_text(state.messages, no - 1), last["weak"]),
                new_answer, RETRY_SCHEMA, "retry", store,
            ):
                st.rerun()
    # 되돌리기는 고친 글을 지우므로 한 번 더 묻는다 (지운 글은 되살릴 수 없음)
    ask_key = f"memo_undo_ask_{result_key}"
    if undo_col.button(":material/undo: 원래 대본으로 되돌리기", key=f"memo_undo_{result_key}", width="stretch"):
        state[ask_key] = True
    if state.get(ask_key):
        st.warning("고친 대본을 지우고 원래 대본으로 되돌릴까요? 지운 글은 되살릴 수 없어요.")
        cancel_col, confirm_col = st.columns(2)
        if cancel_col.button("고친 대본 남기기", key=f"memo_undo_cancel_{result_key}", width="stretch"):
            state.pop(ask_key, None)
            st.rerun(scope="fragment")
        if confirm_col.button(":material/delete: 고친 대본 지우기", key=f"memo_undo_yes_{result_key}", width="stretch"):
            state.pop(ask_key, None)
            state.memo_edits.pop(result_key, None)
            state.memo_results.pop(result_key, None)
            state.memo_draft_reset = result_key
            st.rerun()
    if not practice:
        st.caption(
            f"재도전 검토는 :material/replay: 재도전 탭과 같은 기준으로 채점하고, 질문당 {coach.MAX_RETRIES}번까지예요 "
            f"(지금 {state.retry_counts.get(no, 0)}번). 처음 점수보다 높으면 가장 높은 점수가 종합 점수 · 리포트에 반영돼요. "
            "저장 · 검토 · 되돌리기를 마치면 이 창이 닫혀요."
        )


def show_review_result(no: int, result_key: str, ev: dict | None):
    """'수정하고 재도전 검토 받기' 결과를 바로 아래에: 재도전 탭의 결과와 같은 구조 (show_retry_result)."""
    index = state.memo_reviews.get(result_key)
    history = state.get("retry_history", {}).get(no, [])
    if not ev or not isinstance(index, int) or not 0 <= index < len(history):
        return
    with st.container(border=True):
        st.markdown(f"**:material/fact_check: 재도전 검토 내역** · {index + 1}번째 재도전")
        show_retry_result(no, ev, index, "memo", celebrate=True)


MEMO_SCOPES = ["이번 회차 질문", "다른 질문 연습"]


@st.dialog("지난 회차 답 지우기")
def delete_past_dialog(text: str, rounds: list[int]):
    """지난 회차 답 지우기 확인 창: 경고 · [취소] [삭제]. 같은 답으로 묶인 회차는 함께 지운다."""
    names = " · ".join(f"{r}회차" for r in sorted(rounds))
    st.warning(f"**{names}** 답을 지울까요? 지우면 암기 탭과 다음 회차에서 다시 보이지 않아요.")
    st.caption(f"질문: {text}")
    st.caption("점수와 그래프는 그대로예요. 이미 받아 둔 리포트 파일(.md)에는 답이 남아 있고, "
               "지운 기록은 다음에 받는 리포트에 함께 저장돼요.")
    cancel_col, delete_col = st.columns(2)
    if cancel_col.button("취소", key="past_del_cancel", width="stretch"):
        st.rerun()
    if delete_col.button(f":material/delete: {names} 답 지우기", key="past_del_yes", type="primary", width="stretch"):
        state.setdefault("past_hidden", set()).update((text, r) for r in rounds)
        st.rerun()


def show_past_answers(text: str):
    """지난 회차 답변 보기: 이 질문이 나온 지난 회차마다 그때 최신 답 · 점수 (읽기만).
    대본(고친 대본 · 연습 대본)과 따로 둔다 — 같은 질문에 다르게 답해도 지난 답은 회차 리포트에 그대로 남는다.
    스위치는 질문을 바꿔도 켠 채로 둔다. 외우는 단계(script_hidden)에서는 답이 보이지 않게 접어 둔다."""
    hidden = hidden_past()
    rows = [r for r in coach.question_history(past_reports()).get(text, [])
            if r["round"] != int(state.round) and (text, r["round"]) not in hidden]
    if not rows:
        return
    rounds = " · ".join(f"{r['round']}회차" for r in reversed(rows))
    if not st.toggle(f":material/history: 지난 회차 답변 보기 ({rounds})", key="memo_past_view",
                     help="이 질문이 나온 지난 회차의 답이에요. 대본과 따로 남아서, 이번에 다르게 답해도 지워지지 않아요."):
        return
    if script_hidden():
        st.caption(":material/visibility_off: 지금은 외우는 단계라 지난 답도 가려 뒀어요. 텍스트 모드의 ① · ② 단계에서 볼 수 있어요.")
        return
    # 같은 답(띄어쓰기 · 줄바꿈만 다른 답 포함)이 여러 회차에 있으면 최신 회차 하나만 보여 준다
    groups: dict[str, list[dict]] = {}
    for r in reversed(rows):  # 최근 회차부터
        groups.setdefault(" ".join(r["answer"].split()), []).append(r)
    for same in groups.values():
        r = same[0]
        score = f"{r['score']}/{coach.ANSWER_MAX}점" if isinstance(r["score"], int) else "점수 없음"
        older = " · ".join(f"{x['round']}회차" for x in same[1:])
        also = f" :gray[· {older}와 같은 답]" if older else ""
        with st.container(border=True):
            head_col, del_col = st.columns([6, 1], vertical_alignment="center")
            head_col.markdown(f":gray-badge[{r['round']}회차] :gray[{score}]{also}")
            if del_col.button(":material/delete:", key=f"past_del_{coach.practice_id(text)}_{r['round']}",
                              help="이 지난 회차 답 지우기", width="stretch"):
                delete_past_dialog(text, [x["round"] for x in same])
            if r["answer"].strip():
                # 코드 칸: 오른쪽 위 복사 버튼으로 바로 복사 (한 문장씩 줄을 바꿔 읽기 쉽게)
                st.code("\n".join(coach.split_sentences(r["answer"])), language=None, wrap_lines=True)
            else:
                st.caption("(답 없음)")


def current_answer_label() -> str:
    """암기 탭 답변 보기의 이번 회차 답 이름: '현재 n회차 답'."""
    return f"현재 {int(state.round)}회차 답"


def source_kind(label: str) -> str:
    """답변 보기 이름의 종류: 회차 숫자가 들어간 이름(현재 · 지난 n회차 답 · 내 연습 대본 (n회차))은 숫자를 빼고 본다."""
    if label.startswith("현재 "):
        return "현재 회차 답"
    if label.startswith("지난 "):
        return "지난 회차 답"
    if label.startswith("내 연습 대본"):
        return "내 연습 대본"
    return label


def remember_source(key: str):
    state.memo_source_pref = source_kind(state[key])


def pick_source(col, sources: dict, key: str, help_text: str) -> str:
    """답변 보기: 한 번 고른 종류(예: 만점 예시 · 현재 n회차 답)는 질문을 바꿔도 다른 것을 누를 때까지 그대로.
    그 질문에 그 종류가 없으면 첫 번째(기본)로."""
    options = list(sources)
    match = next((o for o in options if source_kind(o) == state.get("memo_source_pref")), None)
    if match:
        state[key] = match  # 칸을 그리기 전이라 값을 정할 수 있다
    elif state.get(key) not in options:
        state.pop(key, None)
    return col.radio("답변 보기", options, horizontal=True, key=key, help=help_text,
                     on_change=remember_source, args=(key,))


def step_question(key: str, options: list, delta: int):
    """암기 탭 < > 버튼: 고르는 칸(key)을 이전 · 다음 질문으로. 버튼 콜백이라 칸을 그리기 전에 바뀐다."""
    current = state.get(key)
    i = options.index(current) if current in options else 0
    state[key] = options[(i + delta) % len(options)]


def other_questions() -> list[dict]:
    """암기 탭 '다른 질문': 불러온 지난 회차 리포트의 질문(그 회차 최신 답)과 질문 은행의 나머지 질문 (coach.practice_questions)."""
    reports = past_reports()
    try:
        bank = coach.load_questions()
    except (OSError, ValueError, KeyError):
        return []
    return coach.practice_questions(reports, [q["question"] for q in state.questions], bank,
                                    profile["job"], coach.field_of(profile), hidden_past())


def show_memorize():
    st.subheader(":material/psychology: 암기 시뮬레이션")
    st.caption("AI를 부르지 않아요. 핵심어는 간단한 규칙(조사를 뗀 3글자 이상 · 숫자가 든 단어)으로 뽑아서 완벽하지 않을 수 있어요.")

    # 단계 이동 표시가 있으면 모드 · 단계 · 빈칸 양을 그리기 전에 정한다.
    if "go_memo" in state:
        step_mode, step_level = coach.MEMO_STEPS[state.pop("go_memo")]
        state.memo_top = TEXT_MODE
        state.memo_view = coach.MEMO_MODES[step_mode]
        if step_level:
            state.memo_level = step_level
    if "go_speak" in state:
        step, hint = coach.phase_step(state.pop("go_speak"))
        state.memo_top = SPEAK_MODE
        state.speak_step = step
        if hint is not None:
            state.speak_hint = hint

    ev = state.evaluation
    scores = {}
    if ev:
        totals_by_no = {a["no"]: a["score"] for a in ev["answers"]}
        scores = {no: state.retries[no]["score"] if no in state.retries else s for no, s in totals_by_no.items()}
    # 연습할 질문: 이번 회차 질문(점수 · 재도전 검토 있음) / 다른 질문(지난 회차 · 질문 은행, 연습만)
    if state.get("memo_scope") not in MEMO_SCOPES:
        state.memo_scope = MEMO_SCOPES[0]
    scope = st.segmented_control("연습할 질문", MEMO_SCOPES, key="memo_scope", required=True,
                                 help="다른 질문은 지난 회차 질문과 질문 은행의 질문이에요. 연습만 하고 점수에는 들어가지 않아요.")
    practice = None
    if scope == MEMO_SCOPES[0]:
        labels = {
            i + 1: f"질문 {i + 1}" + (f" · {scores[i + 1]}/{coach.ANSWER_MAX}점" if i + 1 in scores else "") + f" · {q['question']}"
            for i, q in enumerate(state.questions)
        }
        question_col, source_col = st.columns([3, 2])
        no = question_col.selectbox("외울 질문", list(labels), format_func=labels.get, key="memo_no")
        question = state.questions[no - 1]
        sources = {current_answer_label(): latest_answer(no)}  # 이번 회차 내 최신 답 (재도전 최고 점수 반영)
        saved = coach.saved_practice(past_reports()).get(question["question"])
        if saved:  # 지난 회차에 고친 연습 대본 (점수에는 들어가지 않는다)
            sources[f"내 연습 대본 ({saved['round']}회차)"] = saved["script"]
        if ev and ev["answers"][no - 1]["needs_rewrite"] and ev["answers"][no - 1]["rewrite"].strip():
            sources["AI 고친 답"] = ev["answers"][no - 1]["rewrite"]
        source = pick_source(source_col, sources, f"memo_source_{no}", "AI 고친 답은 14점 미만인 답에만 있어요.")
        caption = f"질문 {no}" + (f" · 지금 점수 {scores[no]}/{coach.ANSWER_MAX}점" if no in scores else "")
        pick_key, options = "memo_no", list(labels)
    else:
        others = other_questions()
        if not others:
            st.info("연습할 다른 질문이 없어요. 다음 회차 면접을 하면 지난 회차 질문이 여기에 쌓여요.")
            return
        by_id = {q["id"]: q for q in others}
        question_col, source_col = st.columns([3, 2])
        no = question_col.selectbox(
            "외울 질문 (다른 질문 연습)", list(by_id), key="memo_other",
            format_func=lambda i: by_id[i]["question"] + (
                f" · 지난 {by_id[i]['past']['round']}회차" if by_id[i]["past"]
                else f" · {by_id[i]['saved']['round']}회차 연습" if by_id[i]["saved"] else ""),
        )
        question = by_id[no]
        sources = {}
        if question["saved"]:  # 지난 회차에 고치거나 직접 쓴 대본이 있으면 그걸 먼저
            sources[f"내 연습 대본 ({question['saved']['round']}회차)"] = question["saved"]["script"]
        if question["past"]:
            sources[f"지난 {question['past']['round']}회차 답"] = question["past"]["answer"]
        if question["example"]:
            sources["만점 예시"] = question["example"]
        # 지난 회차 답 · 연습 대본이 있으면 빈 '현재 n회차 답' 은 두지 않는다: 지난 답을 고쳐 쓰도록 유도
        # (고쳐 저장하면 이번 회차 연습 대본으로 남는다). 내 답이 하나도 없는 질문만 직접 쓰는 칸을 둔다.
        has_mine = bool(question["past"] or question["saved"])
        add_label = f"{current_answer_label()} 추가"  # 내 답이 없는 질문에 이번 회차 답을 새로 더한다
        if not has_mine:
            sources[add_label] = ""  # 이번 회차에 직접 쓰는 답 (쓰고 저장해야 남는다)
        source = pick_source(source_col, sources, f"memo_source_{no}",
                             "지난 회차 답을 '넓게 열어 고치기' 로 다듬어 쓰면 이번 회차 연습 대본으로 남아요. "
                             "만점 예시는 가상 지원자의 예시라 내 경험에 맞게 고쳐 쓰세요." if has_mine else
                             f"만점 예시는 가상 지원자의 예시라 내 경험에 맞게 고쳐 쓰세요. '{add_label}' 는 "
                             "이 질문에 이번 회차 답을 새로 써서 외우는 칸이에요. 쓰고 저장해야 남아요.")
        practice = {"question": question["question"], "label": source}
        options = list(by_id)
        caption = f"다른 질문 연습 {options.index(no) + 1}/{len(options)} (점수는 이번 회차 면접 답으로만 계산해요)"
        pick_key = "memo_other"
    result_key = f"{no}:{source}"
    original = sources[source].strip()
    text = state.memo_edits.get(result_key, original).strip()  # 고친 대본이 있으면 그걸로 외운다
    # 지금 질문을 크게: 질문을 보고 답하는 연습이라 질문이 화면의 첫 내용이어야 한다
    # 양옆 < > 로 이전 · 다음 질문 (끝에서는 처음으로 돌아간다 · 버튼을 막지 않는다)
    with st.container(border=True, key="memo_qcard"):
        # < > 는 윗줄(질문 번호 · 점수) 양옆에만. 질문 글은 아랫줄에 카드 폭 전체로
        prev_col, body_col, next_col = st.columns([1, 12, 1], vertical_alignment="center")
        prev_col.button(":material/chevron_left:", key="memo_prev", help="이전 질문",
                        on_click=step_question, args=(pick_key, options, -1))
        body_col.caption(caption)
        next_col.button(":material/chevron_right:", key="memo_next_q", help="다음 질문",
                        on_click=step_question, args=(pick_key, options, 1))
        st.markdown(f"#### {question['question']}")
        q_field = question.get("field") or coach.DEFAULT_FIELD
        st.markdown(f":{field_badge(q_field)}-badge[{'공통 질문' if q_field == coach.DEFAULT_FIELD else f'{q_field} 질문'}]")
    if practice and not text:  # 다른 질문: 대본을 직접 쓰면 그때부터 연습할 수 있다
        show_script_editor(no, result_key, original, text, None, practice)
        show_past_answers(question["question"])
        return
    if not text:
        st.info("이 질문에는 아직 외울 답이 없어요. 재도전 탭에서 이 질문에 답하면 여기서 외울 수 있어요.")
        if ev and st.button(":material/replay: 재도전 탭에서 답 쓰기", key=f"memo_empty_go_{no}"):
            state.go_retry_no = no
            state.go_tab = RETRY_TAB
            st.rerun()
        return
    show_script_editor(no, result_key, original, text, ev, practice)
    show_past_answers(question["question"])
    st.divider()

    # 답변 연습: 모드 → 단계 → 단계 내용 순서. 외우는 전략은 두 모드 공통이라 제목 옆 작은 버튼으로.
    title_col, strategy_col = st.columns([4, 1], vertical_alignment="center")
    title_col.subheader(":material/record_voice_over: 답변 연습")
    with strategy_col.popover(":material/push_pin: 전략 보기", width="stretch"):
        show_memo_strategy()
    if state.get("memo_top") not in (TEXT_MODE, SPEAK_MODE):
        state.memo_top = TEXT_MODE
    top = st.segmented_control("모드", [TEXT_MODE, SPEAK_MODE], key="memo_top", required=True, width="stretch")

    if top == SPEAK_MODE:
        show_speaking(result_key, text, question["question"])
        return

    # 텍스트 모드: 누른 단계의 기능만 보인다
    if state.get("memo_view") not in coach.MEMO_MODES:
        state.memo_view = coach.MEMO_MODES[0]
    view = st.segmented_control("단계", coach.MEMO_MODES, key="memo_view", required=True, width="stretch")
    mode_index = coach.MEMO_MODES.index(view)
    level = None
    if mode_index == 0:
        show_memo_skeleton(no, source, text)
    elif mode_index == 1:
        level = show_memo_cloze(no, source, text)
    else:
        show_memo_simulation(result_key, question, text)

    # 지금 단계가 익숙해지면 다음 단계로
    following = coach.next_step(mode_index, level)
    if following is not None and st.button(
        f"다음 단계로 :material/arrow_forward: {coach.step_label(following)}", key=f"memo_next_{mode_index}_{level}"
    ):
        go_memo_step(following)


# 탭 = 단계. 이름 앞 번호로 순서를 보여 주고, 위의 단계 표시가 완료 · 남은 단계를 알려 준다.
CHAT_TAB, EVAL_TAB, RETRY_TAB = ":material/forum: 1. 면접", ":material/bar_chart: 2. 평가", ":material/replay: 3. 재도전"
VERDICT_TAB = ":material/mail: 4. 모의 결과"
LAST_TAB = ":material/live_help: 5. 점검하기"  # 종합 점검 · 사전 정보 탐색 · 마지막에 할 질문
MEMO_TAB = ":material/psychology: 6. 암기"
FEEDBACK_URL = os.getenv("FEEDBACK_SURVEY_URL", "").strip()  # 다 마친 뒤 설문 링크 (.env · Streamlit Secrets)
if not FEEDBACK_URL.startswith("https://"):
    FEEDBACK_URL = ""


def step_status() -> list[dict]:
    """단계마다 이름 · 완료 여부 · 선택 단계 여부. 완료는 그 단계에서 실제로 한 일이 있을 때."""
    tabs = [CHAT_TAB, EVAL_TAB, RETRY_TAB, VERDICT_TAB, LAST_TAB, MEMO_TAB, None]  # 마지막은 리포트 버튼
    return [{"tab": tab, "name": r["item"], "done": r["done"], "optional": r["optional"]}
            for tab, r in zip(tabs, checklist_rows())]


def show_stepper(steps: list[dict]):
    """단계 진행: 'n단계 중 n단계 완료 · 남은 단계 n개' 와 진행 막대만 (탭 이름에 단계 번호가 있어 중복 표시는 하지 않는다)."""
    done = sum(s["done"] for s in steps)
    st.progress(done / len(steps), text=coach.checklist_summary(steps))  # 리포트 창 체크리스트와 같은 문장


def mark_report_downloaded():
    state.report_downloaded = True


def show_finish():
    """마지막 단계(리포트 받기)까지 마치면 설문으로 연결한다. 남은 선택 단계가 있으면 함께 알려 준다."""
    left = [s["name"] for s in step_status() if not s["done"]]
    if left:
        st.success(":material/celebration: 마지막 단계인 리포트까지 받았어요. 수고하셨어요!")
        st.caption(f"남은 선택 단계({' · '.join(left)})는 언제든 이어서 할 수 있어요.")
    else:
        st.success(":material/celebration: 모든 단계를 마쳤어요. 수고하셨어요!")
    if FEEDBACK_URL:
        st.write("서비스를 써 보신 경험을 알려 주시면 더 좋은 연습 도구를 만드는 데 쓸게요. (1~2분)")
        st.link_button("피드백 설문 참여하기", FEEDBACK_URL, icon=":material/rate_review:", type="primary")
    else:
        st.caption(":material/rate_review: 피드백 설문 링크는 준비 중이에요.")

# 탭 · 재도전 질문을 바꾸라는 표시가 있으면, 그리기 전에 정한다 (그린 뒤에는 바꿀 수 없음).
if state.pop("open_eval", False):
    state.view = EVAL_TAB
if state.get("go_tab"):
    state.view = state.pop("go_tab")
if state.get("go_retry_no"):
    state.retry_no = state.pop("go_retry_no")

# 탭은 면접 시작부터 항상 같은 모양 · 같은 key 로 둔다. 화면 구조가 바뀌면
# Streamlit이 대화를 다시 그리면서 스크롤이 맨 위로 올라가기 때문이다.
show_stepper(step_status())
chat_tab, eval_tab, retry_tab, verdict_tab, last_tab, memo_tab = st.tabs(
    [CHAT_TAB, EVAL_TAB, RETRY_TAB, VERDICT_TAB, LAST_TAB, MEMO_TAB], key="view", on_change="rerun"
)

with chat_tab:
    show_messages()
    live = st.container()  # 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나온다
    if state.stage == "done":
        st.success("질문 5개를 모두 마쳤어요. 수고하셨습니다.")
        if state.evaluation:
            st.info("평가가 끝났어요. 위의 :material/bar_chart: 평가 탭에서 확인해 주세요.")
            if st.button(":material/bar_chart: 평가 확인하기", type="primary"):
                state.go_tab = EVAL_TAB
                st.rerun()
        elif st.button("위원 4명에게 평가받기", type="primary"):
            def store(raw):
                state.evaluation = coach.summarize_evaluation(raw, state.questions)
                state.pop("clue_set", None); state.pop("clue_round", None)
                state.go_tab = EVAL_TAB  # 평가가 끝나면 평가 탭으로 바로 이동

            if call_ai(
                "답변을 검토하겠습니다. 위원 4명이 면접 기록을 보고 있어요...",
                coach.build_evaluator(profile),
                coach.format_record(state.questions, state.messages),
                EVAL_SCHEMA, "evaluation", store,
            ):
                st.rerun()

with eval_tab:
    if state.evaluation:
        show_evaluation(state.evaluation)
    elif state.stage == "done":
        st.info(":material/forum: 면접 탭의 '위원 4명에게 평가받기' 버튼을 눌러 주세요.")
    else:
        st.info("질문 5개를 마치면 위원 4명에게 평가받을 수 있어요.")

with retry_tab:
    if state.evaluation:
        show_retry(state.evaluation)
    else:
        st.info("위원 4명에게 평가받은 뒤, 점수가 낮은 질문부터 다시 답해 볼 수 있어요.")

with last_tab:
    show_overview()
    show_precheck()  # 사전 탐색은 면접 전 · 중에도 쓸 수 있게 항상 보인다
    st.divider()
    if state.stage == "done":
        show_last_question()
    else:
        st.info("면접을 마치면 마지막에 할 질문을 추천받고, 내 질문을 다듬을 수 있어요.")

with verdict_tab:
    if state.evaluation:
        show_verdict(state.evaluation)
    else:
        st.info("위원 4명에게 평가받으면 모의 결과를 확인할 수 있어요.")

with memo_tab:
    if state.stage == "done":
        show_memorize()
    else:
        st.info("면접을 마치면 내 답을 외우는 연습을 할 수 있어요.")



@st.dialog("면접 리포트", width="large")
def report_dialog():
    """위쪽 :material/description: 리포트 버튼 · (예전에는 모의 결과의 '성장 리포트 보기' 도) 여는 넓은 창.
    창 안의 다운로드는 창만 다시 그려서, 받은 뒤 마침 안내(설문)가 창 안에 바로 보인다."""
    if state.evaluation:
        show_report(state.evaluation)
        if state.get("report_downloaded"):
            show_finish()
    else:
        st.info("위원 4명에게 평가받으면 면접리포트.md 를 받을 수 있어요. :material/forum: 면접 탭에서 질문 5개를 마친 뒤 평가받아 주세요.")


if state.pop("open_report", False):
    report_dialog()
if state.pop("open_next_round", False) and state.get("evaluation"):
    next_round_dialog()

# 면접이 끝나도 평가받기 전까지는 입력창을 둔다 (맨 아래 고정 입력창이 사라지면 페이지 높이가 바뀌며 스크롤이 튄다).
# 평가를 받은 뒤에는 뺀다: 입력창이 있으면 Streamlit 이 화면을 '맨 아래에 붙여' 두어서,
# 긴 내용이 그려질 때 저절로 맨 아래로 내려가기 때문이다.
if state.stage == "done":
    if not state.evaluation:
        pass_input = st.chat_input("면접이 끝났어요. 위원 4명에게 평가받아 보세요.")
    else:
        pass_input = None
    if pass_input is not None:
        next_button = ":material/bar_chart: 평가 확인하기" if state.evaluation else "위원 4명에게 평가받기"
        with live:
            st.info(f"면접은 끝났어요. '{next_button}' 버튼을 눌러 주세요.")
    st.stop()

answer = st.chat_input(f"답을 적어 주세요 ({coach.MAX_ANSWER_CHARS:,}자까지)", max_chars=coach.MAX_ANSWER_CHARS)
if answer is not None:
    if not answer.strip():
        with live:
            st.info("답을 적은 뒤 보내 주세요.")
        st.stop()

    with live:
        with st.chat_message("user", avatar=AVATARS["user"]):
            st.markdown(answer)

    question = state.questions[state.q_index]
    instructions = coach.build_interviewer(profile, question, state.follow_ups)
    transcript = coach.format_transcript(state.messages + [{"role": "user", "content": answer}])

    try:
        with live, st.spinner("면접관이 답을 읽고 있어요..."):
            result = ask_json(instructions, transcript, INTERVIEWER_SCHEMA, "interviewer")
    except LLMError as e:
        with live:
            st.error(str(e))
        st.stop()

    q = state.q_index
    state.messages.append({"role": "user", "content": answer, "q": q})
    state.understanding = coach.clamp(result.get("understanding"), 0, 100)
    reply = str(result.get("reply", "")).strip()
    ai_wants_follow_up = bool(result.get("follow_up"))
    # 꼬리 질문 뒤 피드백형 면접관: 꼬리 질문의 답 다음 reply 는 피드백이라 AI 가 follow_up 을 잘못 줘도 보여 준다
    feedback_style = coach.persona_of(profile["job"], profile.get("persona_type"))["style"] == "feedback"

    if coach.wants_follow_up(profile, ai_wants_follow_up, state.follow_ups):
        # 꼬리 질문: 같은 질문에 머문다.
        state.follow_ups += 1
        state.messages.append({"role": "assistant", "content": reply, "q": q})
    else:
        # AI가 꼬리 질문을 더 원해도 한도를 넘으면 그 문장(질문)은 보여 주지 않고 넘어간다.
        if reply and (feedback_style or not ai_wants_follow_up):
            state.messages.append({"role": "assistant", "content": reply, "q": q})
        state.q_index += 1
        state.follow_ups = 0
        if state.q_index < coach.TOTAL_QUESTIONS:
            state.messages.append(question_message(state.q_index))
        else:
            state.messages.append({"role": "assistant", "content": "면접을 마치겠습니다."})
            state.stage = "done"
    st.rerun()
