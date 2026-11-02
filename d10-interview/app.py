# Streamlit 화면만. 프롬프트는 prompts.py, AI 호출은 llm.py, 계산은 coach.py.
import contextlib
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
import error_log
import llm
from llm import LLMError, ask_json
from prompts import (
    EVAL_SCHEMA,
    FIELDS,
    HIGHLIGHT_SCHEMA,
    INTERVIEWER_SCHEMA,
    PANEL_CRITERIA,
    PERSONA_CARDS,
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
/* 면접 완료 안내 (show_interview_done): 브랜드 블루 왼쪽 선 · 옅은 바탕. 아래로 내릴 때 입력창 자리만큼 여백 */
.st-key-interview_done {{ background: {"rgba(61, 123, 255, 0.12)" if dark else "#F5F8FE"};
  border: 1px solid {"rgba(141, 180, 255, 0.22)" if dark else "#E6E9F0"}; border-left: 4px solid {"#8DB4FF" if dark else "#0252DE"};
  border-radius: 16px; padding: 20px 24px; gap: 8px; margin-top: 8px; scroll-margin-bottom: 48px; }}
.st-key-interview_done [data-testid="stMarkdown"] {{ margin-bottom: 0 !important; }}
.st-key-interview_done button [data-testid="stMarkdownContainer"] p {{ color: inherit !important; }}
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


def scroll_to_key(key: str):
    """키를 단 칸(st.container(key=...))이 화면 아래쪽에 보이게 바로 내린다 (깜빡임을 줄이려고 기다리지 않고 그려지는 대로).
    스크립트는 고정 문장이고 key(코드에 적힌 글자)와 실행 번호만 넣는다."""
    state["scroll_seq"] = state.get("scroll_seq", 0) + 1
    selector = f".st-key-{key}"
    st.html(
        f"""<script>/* {int(state["scroll_seq"])} */
(() => {{
  let tries = 0;
  const go = () => {{
    const el = document.querySelector({selector!r});
    if (el) {{ el.scrollIntoView({{ block: "end", behavior: "instant" }}); return; }}
    if (++tries < 40) requestAnimationFrame(go);
  }};
  go();
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




# ── 화면 구조 (IA_UserFlow · 원본 IA 이미지 기준) ──────────────────────
# 서비스 접속 → 시작 화면(닉네임 자동 생성) → [+ 새 면접 시작] · [기존 데이터 Markdown 복원] · GNB 1 홈
# GNB 1 홈 · GNB 2 면접 코칭 (면접 데이터 목록 → 회사별 데이터 선택 → 면접 상세: LNB 3개). GNB 3 · 4 는 2차 MVP 라 두지 않는다.
# 면접 진행(파란 흐름): 면접 정보 설정 → 5문항 면접 → [평가 받기] → [평가 확인하기] → 그 회차의 평가 기록
LNB_RECORDS = ":material/history: 면접 기록 (전체)"
LNB_EVAL = ":material/bar_chart: 평가 기록 (회차별)"
LNB_RETRY = ":material/replay: 재도전 (전체)"
LNBS = [LNB_RECORDS, LNB_EVAL, LNB_RETRY]
# 화면 함수들이 쓰던 탭 이름 → LNB (go_tab 으로 이동)
EVAL_TAB, RETRY_TAB, LAST_TAB = LNB_EVAL, LNB_RETRY, LNB_RECORDS
GNB = [("home", ":material/home: 홈"), ("coaching", ":material/forum: 면접 코칭")]
# 회차를 바꾸면 지우는 화면 칸 (질문 번호가 같아도 다른 회차의 글이 남지 않게)
ROUND_WIDGET_PREFIXES = ("retry_answer_", "hl_", "eval_retry_", "clue_retry_", "strategy_", "pending_edit", "retry_no",
                         "eval_rounds", "perfect_hints")
SESSION_ONLY_KEYS = ("highlights", "strategies")  # 회차마다 세션 안에서만 (파일에 남기지 않는다)
NICK_FIRST = ["용감한", "차분한", "꼼꼼한", "부지런한", "단단한", "유쾌한", "성실한", "든든한"]
NICK_SECOND = ["지원자", "디자이너", "개발자", "기획자", "도전자", "준비생"]


def new_nickname() -> str:
    """시작 화면의 닉네임 자동 생성 (홈에서 바꿀 수 있다). 개인정보가 아닌 임의 이름."""
    import random
    return f"{random.choice(NICK_FIRST)} {random.choice(NICK_SECOND)} {random.randint(100, 999)}"


def reset_app():
    """처음 접속: 시작 화면 · 빈 기록 보관함 · 새 닉네임."""
    st.session_state.clear()
    st.session_state.page = "start"
    st.session_state.store_rounds = []
    st.session_state.nickname = new_nickname()
    st.session_state.saved_fingerprint = None
    st.session_state.active_round_id = None
    st.session_state.stage = None


if "page" not in st.session_state:
    reset_app()

state = st.session_state


AVATARS = {"assistant": ":material/support_agent:", "user": ":material/person:"}


def error_session_id() -> str:
    """오류 기록의 세션 ID. 처음 필요할 때 만들고, reset() 이 세션 상태를 비우면 새 면접 세션에서 새로 만든다."""
    if "error_session_id" not in st.session_state:  # 없을 때만 만든다 (같은 면접 세션 동안 유지)
        st.session_state.error_session_id = error_log.new_session_id()
    return st.session_state.error_session_id


def record_ai_event(kind: str, source: str, *, attempt: int, status: str, codes=None, meta=None):
    """AI 호출 실패 · 복구 한 건을 오류 로그에 남긴다. 기록은 실패해도 예외를 내지 않으므로 화면 흐름에 영향이 없다.
    답변 · AI 응답 글 · 예외 메시지는 넘기지 않는다. attempt 는 앱 수준 시도 회차 (SDK 내부 재시도는 알 수 없어 세지 않는다)."""
    meta = {"model": os.getenv("OPENAI_MODEL") or llm.DEFAULT_MODEL, **(meta or {})}
    error_log.record_error(
        kind, source, session_id=error_session_id(), attempt=attempt, status=status, codes=codes,
        meta={k: v for k, v in meta.items() if v is not None},  # 없는 값은 넘기지 않는다 (dropped 를 늘리지 않게)
    )


# 평가 응답 검증 실패 (E-3). 기존 API 오류 문구와 따로 둔다.
INVALID_MESSAGES = {
    "evaluation": "평가 결과를 확인하지 못했어요. 잠시 뒤 다시 평가받아 주세요.",
    "retry": "채점 결과를 확인하지 못했어요. 잠시 뒤 다시 채점해 주세요.",
}

# 앱 수준 자동 재시도 (E-4A): 응답 내용이 잘못된 경우만 최대 1번 더 부른다.
# 연결 · 시간 초과 · 서버 · 호출 제한 오류는 OpenAI SDK 가 이미 2번 더 시도하므로 앱은 다시 부르지 않는다
# (클릭 1번의 실제 HTTP 요청: 최대 4번 = 첫 호출 1 + 앱 재시도 1회 안의 SDK 시도 3).
AUTO_RETRY_KINDS = {"response_parse", "eval_validation"}
AUTO_RETRY_SOURCES = {"interviewer", "evaluation", "retry"}  # 전략 · 형광펜 · 마지막 질문은 제외 (D5)
MAX_APP_ATTEMPTS = 2
RETRY_SPINNER = "응답을 한 번 더 확인하고 있어요."


def run_ai(spinner_text: str, attempt_once, source: str, question_no: int | None = None, container=None):
    """attempt_once() 로 AI 를 부르고 (평가 · 재도전은 그 안에서 검증 · 저장), (성공 여부, 결과, 실패 문구) 를 돌려준다.
    응답 형식 오류 · 평가 검증 실패만 1번 더 부른다. 두 번째 시도의 오류는 유형과 상관없이 다시 부르지 않는다.
    기록: 첫 실패 retrying(1회차) → 재시도 성공 recovered(2회차) 또는 최종 실패 failed(2회차). 재시도 대상이 아니면 failed(1회차)."""
    retried = None
    for attempt in range(1, MAX_APP_ATTEMPTS + 1):
        try:
            with container if container is not None else contextlib.nullcontext(),                     st.spinner(spinner_text if attempt == 1 else RETRY_SPINNER):
                result = attempt_once()
        except LLMError as e:
            kind, message, codes = e.kind, str(e), [e.code] if e.code else None
            meta = {"http_status": e.http_status, "exception": e.exception}
        except coach.EvaluationInvalid as e:
            kind, message, codes = "eval_validation", INVALID_MESSAGES[source], e.codes
            meta = {"item_count": len(e.codes)}
        else:
            if retried:
                record_ai_event(retried, source, attempt=attempt, status="recovered", meta={"question_no": question_no})
            return True, result, None
        again = attempt < MAX_APP_ATTEMPTS and source in AUTO_RETRY_SOURCES and kind in AUTO_RETRY_KINDS
        record_ai_event(kind, source, attempt=attempt, status="retrying" if again else "failed", codes=codes,
                        meta={**meta, "question_no": question_no})
        if not again:
            return False, None, message
        retried = kind
    return False, None, None  # 닿지 않음 (마지막 시도는 항상 위에서 돌아간다)


def call_ai(spinner_text: str, instructions: str, user_input: str, schema: dict, name: str, store,
            question_no: int | None = None) -> bool:
    """AI를 부르고, 결과를 받자마자 store(결과) 로 저장한다. 실패하면 한국어 한 줄 에러 + 오류 기록.
    Streamlit 은 응답을 기다리는 동안 다른 버튼을 누르면 실행을 멈추고 다시 시작한다.
    저장을 화면 그리기 뒤로 미루면 받은 결과를 버리고 다시 호출하게 돼서, spinner 안에서 바로 저장한다.
    평가 · 재도전 store 는 맨 앞에서 검증하고 통과하지 못하면 EvaluationInvalid 를 낸다 → 아무것도 바뀌지 않는다.
    자동 재시도는 run_ai (store 는 성공한 응답으로 한 번만 불린다)."""
    ok, _, message = run_ai(spinner_text, lambda: store(ask_json(instructions, user_input, schema, name)),
                            name, question_no)
    if not ok:
        st.error(message)
    return ok


def question_message(index: int, questions: list[dict] | None = None) -> dict:
    question = (questions if questions is not None else state.questions)[index]
    field = question.get("field", coach.DEFAULT_FIELD)
    tag = f" :material/explore: **{field} 질문**" if field != coach.DEFAULT_FIELD else ""
    text = f"**질문 {index + 1}/{coach.TOTAL_QUESTIONS}.**{tag} {question['question']}"
    return {"role": "assistant", "content": text, "q": index, "kind": "question"}


# 리포트 복원 안내 (E-5). 손상된 데이터는 0점으로 채우지 않고 원본을 남긴 채 읽을 수 있는 것만 불러온다.
RESTORE_EVAL_UNREADABLE = "평가 데이터를 읽지 못해 질문과 답변만 불러왔어요. 다시 평가받을 수 있어요."
RESTORE_RETRY_UNREADABLE = "일부 재도전 평가를 읽지 못했어요. 답변은 보존했지만 해당 점수는 반영하지 않았어요."


def report_restore_problems(problems: dict) -> list[str]:
    """복원하며 찾은 문제를 오류 로그에 남기고 화면 안내 문장을 돌려준다 (문제 코드 · 개수만, 답 · 평가 글은 넘기지 않음)."""
    warnings = []
    if problems["evaluation"]:
        error_log.record_error("restore_validation", "restore", session_id=error_session_id(), codes=problems["evaluation"],
                               meta={"item_count": len(problems["evaluation"])})
        warnings.append(RESTORE_EVAL_UNREADABLE)
    if problems["retry_unreadable"]:
        if problems["retry_codes"]:  # 이번에 새로 읽지 못한 기록이 있을 때만 기록 (지난번에 남겨 둔 것은 다시 세지 않음)
            error_log.record_error("restore_validation", "restore", session_id=error_session_id(),
                                   codes=sorted(set(problems["retry_codes"])), meta={"item_count": len(problems["retry_codes"])})
        warnings.append(RESTORE_RETRY_UNREADABLE)
    return warnings


# 로고: 라이트는 파랑(logo.png), 다크는 은색(logo_dark.png). 테마는 hover_css 와 같은 방법으로 안다
_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO = os.path.join(_ASSETS, "logo_dark.png" if getattr(st.context.theme, "type", None) == "dark" else "logo.png")


def field_examples() -> str:
    """분야 예시 이름 몇 개 (공통 분야 추천 문장용)."""
    return " · ".join(name for name in FIELDS if name != coach.DEFAULT_FIELD)


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
            # 기본 2개 + 나머지는 [더 보기] (D6). AI 가 쓴 순서를 중요도로 보지 않고 받은 순서 그대로 보여 준다
            for item in hint["check"][:coach.SHOW_ITEMS]:
                st.markdown(f":material/fact_check: **면접 전 확인:** {item}")
            if len(hint["check"]) > coach.SHOW_ITEMS:
                with st.expander(f"더 보기 · {len(hint['check']) - coach.SHOW_ITEMS}개"):
                    for item in hint["check"][coach.SHOW_ITEMS:]:
                        st.markdown(f":material/fact_check: **면접 전 확인:** {item}")


def show_clues(ev: dict):
    """역전의 실마리: 가장 낮은 답 MAX_CLUES 개와 각 답의 가장 낮은 기준. 고르는 건 코드(coach.pick_clues).
    찾은 실마리는 state.clue_set 에 고정해 둔다 (재도전 뒤에도 같은 실마리에 '역전 성공! 전 → 후' 를 보여 주려고).
    실마리를 모두 재도전하면 '역전의 실마리 찾기' 로 최신 점수에서 다시 찾는다."""
    retries, retry_counts = state.get("retries", {}), state.get("retry_counts", {})
    if "clue_set" not in state:
        state.clue_set = coach.pick_clues(ev, retries=retries, retry_counts=retry_counts)
    clues = state.clue_set
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
    st.caption(f"점수가 가장 낮은 답 {len(clues)}개예요. 여기부터 고치면 점수가 가장 많이 올라요.")
    for clue, row in zip(clues, progress["rows"]):
        with st.container(border=True):
            st.markdown(
                f"**질문 {clue['no']}** · {clue['score']}/{coach.ANSWER_MAX}점 · "
                f"가장 약한 기준 **{clue['name']} {clue['criterion_score']}/{coach.CRITERION_MAX}**"
            )
            st.caption(clue["question"])
            if row["up"]:
                st.success(f":material/trending_up: **역전 성공!** {row['before']} → {row['after']}점 (+{row['diff']})")
            if row["retried"] and not row["up"]:
                st.info(f"재도전 완료 · {row['before']} → {row['after']}점 ({row['diff']:+d}). 한 번 더 도전해 볼 수 있어요.")
            elif not row["up"]:
                st.markdown(f"**가장 약한 점:** {clue['weak']}")
                st.caption(f"'역전의 기회 잡기' 를 누르면 아래에서 질문 {clue['no']} 의 형광펜 · 전략 가이드를 보며 다시 답할 수 있어요.")
            if not row["up"]:
                # 재도전 횟수 제한 없음 (E-4B): 횟수 표시 · 꺼진 버튼 없이 언제나 누를 수 있다
                name = "한 번 더 도전하기" if row["retried"] else "역전의 기회 잡기"
                if st.button(f":material/replay: {name}", key=f"clue_retry_{clue['no']}",
                             type="secondary" if row["retried"] else "primary"):
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
    st.caption("같은 회사 · 직군의 지난 회차 기록이에요. 점수는 그 회차 최신 점수이고, 이번 회차 종합 점수에는 들어가지 않아요.")
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
    재도전 (전체) 화면이 쓴다."""
    history = state.setdefault("retry_history", {}).setdefault(no, [])
    attempt["attempt_id"] = coach.next_attempt_id(no, history, state.get("retry_unreadable", {}).get(no, []))
    history.append(attempt)
    state.retry_counts[no] = len(history)  # 횟수는 기록 개수 (제한 없음 · 실마리 진행 · 옛 리포트 호환용)
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
    """재도전 결과 하나 (전 → 후).
    index: retry_history 안의 몇 번째 재도전인지. place: 두 탭이 함께 그려져도 칸 key 가 겹치지 않게.
    celebrate: 점수가 오르면 '역전 성공!' 을 여기서 띄운다 (재도전 탭은 실마리 카드에만 띄우므로 False)."""
    last = ev["answers"][no - 1]
    question = state.questions[no - 1]
    history = state.get("retry_history", {}).get(no, [])
    result = history[index]
    reflected = state.retries.get(no)  # 종합 점수에는 최고 점수 (coach.reflected_retry)
    # 비교 기준: 이 재도전 바로 전까지의 최고 점수 (같은 회차 · 질문, PRD 8.2). 앞선 재도전이 최초보다 높지 않으면 최초 답
    before_best = coach.reflected_retry(last["score"], history[:index])
    base = before_best or last
    diff = coach.compare(base["scores"], result["scores"])
    st.caption(f":material/compare_arrows: 비교 기준: "
               + (f"이전 최고 점수 ({history.index(before_best) + 1}번째 재도전 · {base['score']}점)" if before_best
                  else f"최초 답 ({base['score']}점)"))
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
    show_panel_coaching(base["scores"], result["scores"])


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

    def label(a: dict) -> str:  # 재도전 횟수 제한 · 카운터 없음 (E-4B)
        first = original[a["no"]]["score"]
        score = f"{first} → {a['score']}" if a["score"] != first else f"{first}"
        return f"질문 {a['no']} · {score}/{coach.ANSWER_MAX}점 · {a['question']}"

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
        # 채점하지 못한 답 (E-4A, 세션 안에서만): 다른 질문으로 갔다 와도 칸에 다시 채운다.
        # Streamlit 은 화면에 그리지 않은 칸의 값을 지우므로 질문별로 따로 보관한다.
        answer_key = f"retry_answer_{no}"
        unscored = state.setdefault("retry_pending", {})
        if no in unscored and answer_key not in state:
            state[answer_key] = unscored[no]

        def keep_unscored():  # 보관 중인 답을 고치면 고친 글을 보관한다
            if no in unscored:
                unscored[no] = state[answer_key]

        new_answer = st.text_area(
            "다시 답하기", height=180, key=answer_key, max_chars=coach.MAX_ANSWER_CHARS, on_change=keep_unscored
        )
        if no in unscored:
            st.info("채점하지 못한 답변이 남아 있어요. 다시 채점할 수 있어요.")
        if st.button("다시 채점", type="primary"):
            if not new_answer.strip():
                st.info("다시 쓴 답을 적은 뒤 눌러 주세요.")
            elif " ".join(new_answer.split()) in graded_answers(no):
                # 같은 질문에서 이미 채점에 성공한 답 (면접 때 답 · 재도전 기록): AI 를 다시 부르지 않는다 (기록 · 최고 점수 그대로)
                st.info("이미 채점받은 답변이에요. 답변을 수정하면 다시 채점받을 수 있어요.")
            else:
                def store(raw):
                    attempt = {"answer": new_answer.strip(), **coach.checked_retry(raw)}  # 검증 실패면 여기서 멈춤
                    record_retry(no, attempt, last["score"])
                    unscored.pop(no, None)  # 채점 성공: 보관한 답 정리
                    if attempt["score"] > last["score"]:
                        state.scroll_top = True  # 역전 성공: 결과가 맨 위에 오므로 페이지 맨 위로

                if call_ai(
                    "다시 쓴 답을 채점하고 있어요...",
                    coach.build_retry(profile, question, before, last["weak"]),
                    new_answer.strip(), RETRY_SCHEMA, "retry", store, question_no=no,
                ):
                    st.rerun()
                else:
                    unscored[no] = new_answer  # 실패: 쓴 답을 질문별로 보관 (기록 · 횟수 · 최고 점수는 그대로)

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


OVERVIEW_COLORS = {"공통": "#AEB0B6", "헬스케어": "#38BDF8"}  # 회차 태그와 같은 계열 (그 밖 분야는 보라)


def show_overview(group: list[dict]):
    """면접 기록 (전체)의 전체 회차 종합 · 진행도 (공통/분야): 이 회사(또는 '기타') · 직군의 회차만.
    회차마다 최신 종합 점수를 분야 색으로 (공통 회색 · 헬스케어 하늘색 …). 둘 다 합격선을 넘도록 안내한다 (고정 문장 · 숫자는 앱 계산)."""
    reports = [coach.round_as_report(r) for r in group if r.get("stage") in ("done", "summary")]
    rounds = coach.round_overview([r for r in reports if r["total_latest"] is not None or r["scores"]])
    if not rounds:
        st.caption("평가받은 회차가 생기면 전체 회차 종합 · 진행도를 보여 드려요.")
        return
    st.subheader(":material/insights: 전체 회차 종합 · 공통과 분야 면접")
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
    st.subheader(":material/timeline: 전체 회차 진행도 · 공통과 분야")
    counts = {}
    for r in rows:
        counts[r["field"]] = counts.get(r["field"], 0) + 1
    st.caption(f"진행한 회차 {len(rows)}번 · " + " · ".join(f"{f} {n}번" for f, n in counts.items()))
    asked = {q for r in reports for q in r["questions"]}
    try:
        coverage = coach.question_coverage(coach.load_questions(), group[0]["job"], asked,
                                           [coach.DEFAULT_FIELD, *[f for f in counts if f != coach.DEFAULT_FIELD]])
    except (OSError, ValueError, KeyError):
        coverage = []
    for cov in coverage:
        label = "공통 질문" if cov["field"] == coach.DEFAULT_FIELD else f"{cov['field']} 질문"
        st.progress(cov["asked"] / cov["total"], text=f"{label} {cov['asked']}/{cov['total']}개 나옴 (질문 은행 기준)")
    st.caption("공통 질문은 분야와 상관없이 어느 면접에서나 나와요. 다 나온 뒤에는 '새 질문으로' 를 골라도 나온 질문이 다시 섞여요.")
    for kind, message in coach.overview_advice(best):
        getattr(st, kind)(message)


def user_now() -> datetime:
    """사용자 브라우저 시간대의 지금 시각. 배포 서버 시계는 UTC 라서 그대로 쓰지 않는다."""
    try:
        tz = ZoneInfo(st.context.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz)


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
        title, body = "모의면접 합격입니다. 당신의 가능성을 증명했습니다.", "실전처럼 소리 내어 답해 보며 감각을 유지하세요."
    elif result["level"] == "candidate":
        title = "합격 후보로 선정되었습니다."
        body = (f"합격선(위원 평균 {coach.PASS_PANEL:.1f} · 종합 {coach.PASS_TOTAL})까지 <b>{need}</b> 남았어요. "
                + (next_round if result["panel_short"] else
                   "경쟁률이 높을 경우 재도전으로 대답을 수정해 다듬어보세요."))
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
                               help="면접 정보 설정으로 가요. 같은 회사 · 직군으로 분야별 면접을 고를 수 있어요."):
        state.open_next_round = True
        st.rerun()
    # 왼쪽 재도전 · 오른쪽 성장 리포트 (둘 다 같은 보통 버튼). 합격이면 재도전 칸 없이 리포트가 왼쪽에.
    first_col, second_col = st.columns(2)
    if not result["passed"] and first_col.button(":material/replay: 재도전으로 점수 올리기", width="stretch"):
        state.go_tab = RETRY_TAB
        st.rerun()
    report_col = first_col if result["passed"] else second_col
    if report_col.button(":material/insights: 전체 회차 종합 보기", width="stretch"):
        state.go_tab = LAST_TAB  # 면접 기록 (전체)의 전체 회차 종합 · 진행도로
        st.rerun()


def graded_answers(no: int) -> set[str]:
    """이 질문에서 이미 채점받은 답 (면접 때 답 · 재도전한 답). 띄어쓰기 · 줄바꿈 차이는 같은 답으로 본다."""
    def norm(s: str) -> str:
        return " ".join(s.split())
    answers = [coach.answer_text(state.messages, no - 1)] + [a["answer"] for a in state.get("retry_history", {}).get(no, [])]
    return {norm(a) for a in answers if a.strip()}


live = None  # 면접 화면에서 정한다: 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나오는 칸

PENDING_MESSAGE = "답변을 보관했어요. 다시 보내거나 수정할 수 있어요."
PENDING_EDIT_KEY = "pending_edit_text"


def clear_pending_answer():
    for key in ("pending_answer", "pending_editing", PENDING_EDIT_KEY):
        state.pop(key, None)


def show_pending_answer(pending: dict, typed: str | None) -> str | None:
    """면접관에게 전달하지 못한 답 (E-4A). [다시 시도] · [수정한 답변 보내기] 를 누르면 보낼 글을 돌려준다.
    보관한 답은 사용자가 이 두 버튼으로 보낼 때만 바뀐다. 입력창에 새로 쓴 글은 바로 보내지 않고 수정 칸에 옮겨 둔다."""
    moved = typed is not None and bool(typed.strip())
    if moved:
        state[PENDING_EDIT_KEY] = typed  # 수정 칸을 그리기 전이라 값을 넣을 수 있다
        state.pending_editing = True
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(pending["text"])
        st.caption(":material/schedule_send: 아직 면접관에게 전달되지 않은 답변이에요.")
    if pending.get("error"):
        st.error(pending["error"])
    st.info(PENDING_MESSAGE)
    if moved:
        st.caption("새로 쓴 답변은 아래 수정 칸에 옮겨 두었어요. '수정한 답변 보내기' 를 눌러야 바뀌어요.")
    if state.get("pending_editing"):
        if PENDING_EDIT_KEY not in state:
            state[PENDING_EDIT_KEY] = pending["text"]
        text = st.text_area("답변 수정", key=PENDING_EDIT_KEY, height=160, max_chars=coach.MAX_ANSWER_CHARS)
        send_col, cancel_col = st.columns(2)
        if send_col.button("수정한 답변 보내기", key="pending_send_edit", type="primary", width="stretch"):
            if text.strip():
                return text
            st.info("답을 적은 뒤 보내 주세요.")
        if cancel_col.button("수정 취소", key="pending_cancel_edit", width="stretch"):
            state.pending_editing = False
            state.pop(PENDING_EDIT_KEY, None)
            st.rerun()
        return None
    retry_col, edit_col = st.columns(2)
    if retry_col.button(":material/refresh: 다시 시도", key="pending_resend", type="primary", width="stretch"):
        return pending["text"]
    if edit_col.button(":material/edit: 답변 수정", key="pending_edit", width="stretch"):
        state.pending_editing = True
        st.rerun()
    return None


def send_answer(text: str, show_bubble: bool):
    """답 하나를 면접관에게 보낸다. AI 를 부르기 전에 답을 보관하고 (pending_answer), 성공했을 때만 대화 기록에 넣는다.
    실패하면 보관한 답 · 오류 문구를 남기고 다음 화면에서 [다시 시도] · [답변 수정] 을 보여 준다 (질문은 넘어가지 않음)."""
    q, follow_ups = state.q_index, state.follow_ups
    pending = {"q": q, "follow_ups": follow_ups, "text": text}
    state.pending_answer = pending
    state.pending_editing = False
    state.pop(PENDING_EDIT_KEY, None)
    if show_bubble:
        with live:
            with st.chat_message("user", avatar=AVATARS["user"]):
                st.markdown(text)

    question = state.questions[q]
    instructions = coach.build_interviewer(profile, question, follow_ups)
    transcript = coach.format_transcript(state.messages + [{"role": "user", "content": text}])
    ok, result, message = run_ai(
        "면접관이 답을 읽고 있어요...",
        lambda: ask_json(instructions, transcript, INTERVIEWER_SCHEMA, "interviewer"),
        "interviewer", container=live,
    )
    if not ok:
        pending["error"] = message  # 다음 화면에서 보관한 답 아래에 보여 준다
        st.rerun()
    # 같은 답이 두 번 들어가지 않게: 지금 보관 중인 답이 이번에 보낸 답이고, 질문 위치가 그대로일 때만 반영한다
    if state.get("pending_answer") is not pending or (state.q_index, state.follow_ups) != (q, follow_ups):
        st.rerun()
    clear_pending_answer()

    state.messages.append({"role": "user", "content": text, "q": q})
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
            state.finish_scroll = True  # 입력창이 사라지면 화면이 맨 위로 가서, 다음 화면에서 완료 안내로 내린다
    st.rerun()


def interview_turn():
    """면접 중 답 한 번: 보관한 답이 있으면 [다시 시도] · [답변 수정] 부터, 없으면 입력창의 새 답."""
    last = state.q_index == coach.TOTAL_QUESTIONS - 1
    answer = st.chat_input(f"{'마지막 질문이에요. ' if last else ''}답을 적어 주세요 ({coach.MAX_ANSWER_CHARS:,}자까지)",
                           max_chars=coach.MAX_ANSWER_CHARS)
    pending = state.get("pending_answer")
    if pending:
        # 전달하지 못한 답이 있으면 그 답부터: 사용자가 [다시 시도] 또는 [수정한 답변 보내기] 를 눌렀을 때만 보낸다
        with live:
            to_send = show_pending_answer(pending, answer)
        if to_send is None:
            return
        send_answer(to_send, show_bubble=to_send != pending["text"])
    elif answer is not None:
        if not answer.strip():
            with live:
                st.info("답을 적은 뒤 보내 주세요.")
            return
        send_answer(answer, show_bubble=True)


# ── 면접 기록 보관함 (세션): 회차 레코드 목록 · 지금 고른 회차 ─────────────────
def all_rounds() -> list[dict]:
    return state.store_rounds


def find_round(round_id: str | None) -> dict | None:
    return next((r for r in state.store_rounds if r["round_id"] == round_id), None) if round_id else None


def active_round() -> dict | None:
    return find_round(state.get("active_round_id"))


def sync_active():
    """지금 화면 상태(고른 회차를 펼친 것)를 그 회차 레코드에 돌려 쓴다. 매 실행 처음 · 회차를 바꾸기 전 · 저장 전에 부른다."""
    record = active_round()
    if record is None:
        return
    for key in coach.ROUND_STATE_KEYS:
        if key in state:
            record[key] = state[key]
        elif key in ("clue_set", "pending_answer"):  # 화면 함수가 지워서 '없음' 을 뜻하는 칸
            record[key] = None
    for key in SESSION_ONLY_KEYS:
        record[key] = state.get(key, {})
    record["stage"] = state.stage


def load_round(round_id: str):
    """회차 하나를 화면 상태로 펼친다 (지금 회차는 먼저 레코드에 돌려 쓴다). 다른 회차의 입력 칸 글은 지운다."""
    global profile
    sync_active()
    record = find_round(round_id)
    if record is None:
        return
    for key in [k for k in state if str(k).startswith(ROUND_WIDGET_PREFIXES)]:
        del state[key]
    for key in ("pending_editing", "scroll_top", "scroll_retry", "clue_updated", "eval_done_round"):
        state.pop(key, None)
    for key in coach.ROUND_STATE_KEYS:
        if record.get(key) is None and key in ("clue_set", "pending_answer"):
            state.pop(key, None)
        else:
            state[key] = record.get(key)
    for key in SESSION_ONLY_KEYS:
        state[key] = record.setdefault(key, {})
    state.stage = record["stage"]
    state.questions = record["questions"]
    state.round = record["round_number"]
    state.active_round_id = round_id
    profile = coach.round_profile(record)  # 화면 함수 · 프롬프트가 쓰는 지원 정보
    previous = coach.previous_evaluated(all_rounds(), record)
    state.previous = coach.round_as_report(previous) if previous else None


def past_reports() -> list[dict]:
    """지금 회차와 같은 회사(또는 '기타') · 직군의 다른 회차 (리포트 모양). 다른 회사 · 직군 기록은 섞지 않는다."""
    record = active_round()
    if record is None:
        return []
    return [coach.round_as_report(r) for r in coach.group_rounds(all_rounds(), record.get("company_key"), record["job"])
            if r is not record and r.get("stage") in ("done", "summary")]


def unsaved() -> bool:
    """마지막으로 받은 파일 뒤에 바뀐 기록이 있는가 (파일에 들어갈 내용으로 비교)."""
    if not coach.savable_rounds(all_rounds()):
        return False
    return coach.store_fingerprint(all_rounds(), state.nickname) != state.get("saved_fingerprint")


def group_label(key: str | None) -> str:
    return key or coach.OTHER_GROUP


def go_page(page: str):
    state.page = page
    state.page_top = True  # 다른 화면으로 가면 맨 위부터 (면접 화면은 입력창 때문에 맨 아래에 붙어 있다)


def open_group(key: str | None, job: str, lnb: str | None = None):
    """면접 상세(LNB)로. lnb 를 주면 그 탭, 안 주면 사용자가 마지막에 고른 탭 (없으면 면접 기록).
    LNB 위젯 키(lnb)는 위젯을 그린 뒤에는 바꿀 수 없어서 (StreamlitAPIException), 갈 탭은 lnb_target 에 두고
    page_coaching 이 LNB 를 그리기 직전에 옮긴다. 버튼 처리 중 · 콜백 · 화면 흐름 어디서 불러도 같다."""
    state.page = "coaching"
    state.page_top = True
    state.coach_group = {"key": key, "job": job}
    state.lnb_target = lnb or (state.get("lnb_choice") if state.get("lnb_choice") in LNBS else LNB_RECORDS)


def open_round(round_id: str, lnb: str):
    """회차를 고르고 그 회사 · 직군의 면접 상세(LNB)로."""
    load_round(round_id)
    record = active_round()
    open_group(record.get("company_key"), record["job"], lnb)


def open_setup(company: str = "", job: str | None = None, company_desc: str = ""):
    """[+ 새 면접 시작] → 면접 정보 설정. 같은 회사 · 직군에서 이어 가면 칸을 채워 둔다."""
    state.page = "setup"
    state.f_company = company
    state.f_company_desc = company_desc
    if job in coach.JOBS:
        state.f_job = job


def request_evaluation() -> bool:
    """[평가 받기]: 지금 회차의 최초 답 5개를 위원 4명이 평가 (응답 검증 · 자동 재시도 1회는 call_ai)."""
    def store(raw):
        state.evaluation = coach.checked_evaluation(raw, state.questions)  # 검증 실패면 저장 없이 멈춤
        # 부분 복원 뒤 다시 평가받은 경우: 남아 있던 재도전 기록으로 최고 점수를 다시 고른다 (보통은 기록이 없음)
        state.retries = coach.reflected_retries(state.evaluation, state.get("retry_history", {}))
        state.pop("clue_set", None); state.pop("clue_round", None)

    return call_ai(
        "답변을 검토하겠습니다. 위원 4명이 면접 기록을 보고 있어요...",
        coach.build_evaluator(profile), coach.format_record(state.questions, state.messages),
        EVAL_SCHEMA, "evaluation", store,
    )


def round_label(record: dict) -> str:
    kind = coach.INTERVIEW_TYPES[record.get("interview_type", "common")]
    field = "" if record.get("interview_type") == "common" else f" · {record.get('field')}"
    return f"{record['round_number']}회차 · {kind}{field} · {record.get('date', '')} · {coach.round_status(record)}"


def round_totals(record: dict) -> tuple[int | None, int | None]:
    ev = record.get("evaluation")
    if ev:
        totals = coach.total_scores(ev, record.get("retries") or {})
        return totals["first"], totals["latest"]
    scores = (record.get("summary") or {}).get("scores") or []
    return (sum(scores) if scores else None), (record.get("summary") or {}).get("total_latest")


# ── 데이터 저장하기 (Markdown v2 통합 저장) ────────────────────────────
def mark_saved(fingerprint: str):
    state.saved_fingerprint = fingerprint


@st.dialog("데이터 저장하기", width="large")
def save_dialog():
    """전체 기록(여러 회사 · 직군 · 회차)을 Markdown v2 파일 하나로 내려받는다. 기존 파일은 덮어쓰지 않는다 (새 파일 다운로드)."""
    sync_active()
    rounds = all_rounds()
    kept = coach.savable_rounds(rounds)
    running = [r for r in rounds if r not in kept]
    if not kept:
        st.info("저장할 면접 기록이 없어요. 면접 질문 5개를 마치면 저장할 수 있어요.")
        return
    groups = {(r.get("company_key"), r["job"]) for r in kept}
    st.markdown(f"**회사 · 직군 {len(groups)}곳 · 회차 {len(kept)}개**를 파일 하나로 저장해요.")
    if running:
        st.caption(f":material/info: 진행 중인 면접 {len(running)}개는 저장되지 않아요. 질문 5개를 마친 뒤 저장해 주세요.")
    st.warning(":material/lock: 파일에는 닉네임 · 회사 · 내 경험 원문 · 면접 대화 · 답변이 들어가요. 다른 사람과 공유할 때 주의해 주세요.")
    # 위 안내를 확인했다고 체크해야 다운로드할 수 있다 (사용자 요청 — CLAUDE.md '버튼을 disabled 로 막지 말 것' 의 예외)
    agreed = st.checkbox("위 안내를 확인했어요. 개인정보가 들어간 파일이라는 걸 알고 내려받을게요.", key="save_agree")
    now = user_now()
    fingerprint = coach.store_fingerprint(rounds, state.nickname)
    file_name = coach.store_file_name(now.date())
    st.download_button(
        f":material/download: {file_name} 다운로드",
        data=coach.build_store_file(rounds, state.nickname, now.strftime("%Y-%m-%d %H:%M"), now.date()),
        file_name=file_name, mime="text/markdown", type="primary", disabled=not agreed,
        on_click=mark_saved, args=(fingerprint,), key="save_download",
    )
    if not agreed:
        st.caption(":material/info: 위 안내를 확인하고 체크하면 다운로드 버튼이 켜져요.")
    elif state.get("saved_fingerprint") == fingerprint:
        st.success(":material/check: 지금 기록을 저장했어요. 다음에 이 파일을 'Markdown 복원' 에서 올리면 이어서 할 수 있어요.")
    st.caption("저장할 때마다 새 파일로 내려받아요. 컴퓨터에 있는 기존 파일은 바뀌지 않아요.")


# ── 공통 머리 (로고 · GNB · 공통 기능) ─────────────────────────────
def show_header():
    with st.container(key="logo_bar"):
        st.image(LOGO)
        st.button("홈으로 돌아가기", key="logo_home", on_click=go_page, args=("home",))
    with st.container(horizontal=True, gap="small", key="gnb"):
        for page, label in GNB:
            current = state.page == page
            st.button(label, key=f"gnb_{page}", type="primary" if current else "secondary", on_click=go_page, args=(page,))
        st.button(":material/add: 새 면접 시작", key="gnb_new", on_click=open_setup)
        if st.button(":material/save: 데이터 저장하기", key="gnb_save"):
            save_dialog()
        st.button(":material/upload_file: Markdown 복원", key="gnb_restore", on_click=go_page, args=("restore",))
    if unsaved():
        st.caption(":material/warning: 마지막 저장 뒤에 바뀐 기록이 있어요. 창을 닫거나 새로고침하면 사라지니 '데이터 저장하기' 로 받아 두세요.")


def show_notices():
    if state.get("notice"):
        st.info(state.pop("notice"))
    for warning in state.pop("notice_warnings", None) or []:
        st.warning(warning)


# ── 시작 화면 ──────────────────────────────────────────────────
def start_to(page: str):
    state.page = page


def page_start():
    """시작 화면: 로고 + 닉네임 자동 생성 + 시작 경로 (새 면접 · Markdown 복원 · 홈)."""
    with st.container(key="title_screen"):
        st.image(LOGO)
        with st.container(key="title_stage"):
            if not state.get("splash_done"):
                state.splash_done = True
                with st.container(key="splash_text"):
                    with st.container(key="splash_head"):
                        st.markdown("질문을 파악하고, 전략을 강화하라!")
                    with st.container(key="splash_sub"):
                        st.markdown("합격을 향한 전세역전(戰勢逆轉) 취업 코칭 서비스")
            with st.container(key="title_body"):
                st.markdown(f"반가워요, **{html.escape(state.nickname)}** 님. 닉네임은 홈에서 바꿀 수 있어요.")
                with st.container(key="title_menu"):
                    st.button(":material/add: 새 면접 시작", key="title_new", type="primary", width="stretch",
                              on_click=open_setup)
                    st.button(":material/upload_file: 기존 데이터 Markdown 복원", key="title_resume", width="stretch",
                              on_click=start_to, args=("restore",))
                    st.button(":material/home: 홈", key="title_home", width="stretch", on_click=start_to, args=("home",))


# ── GNB 1 · 홈 ────────────────────────────────────────────────
def set_nickname():
    name = " ".join(str(state.get("nickname_input", "")).split())[:MAX_NICKNAME_CHARS]
    if name:
        state.nickname = name


MAX_NICKNAME_CHARS = 20


def page_home():
    st.title("홈")
    state.setdefault("nickname_input", state.nickname)
    st.text_input("닉네임", key="nickname_input", max_chars=MAX_NICKNAME_CHARS, on_change=set_nickname,
                  help="자동으로 만든 닉네임이에요. 바꾸면 면접 인사 · 저장 파일에 이 이름이 들어가요.")
    rounds = all_rounds()
    groups = {(r.get("company_key"), r["job"]) for r in rounds}
    running = [r for r in rounds if r.get("stage") == "interview"]
    a, b, c = st.columns(3)
    a.metric("회사 · 직군", len(groups))
    b.metric("면접 회차", len(rounds))
    c.metric("진행 중 면접", len(running))
    st.subheader("바로 가기")
    with st.container(horizontal=True, gap="small"):
        st.button(":material/add: 새 면접 시작", key="home_new", type="primary", on_click=open_setup)
        st.button(":material/forum: 면접 기록 보기", key="home_records", on_click=go_page, args=("coaching",))
        if st.button(":material/save: 데이터 저장하기", key="home_save"):
            save_dialog()
        st.button(":material/upload_file: Markdown 복원", key="home_restore", on_click=go_page, args=("restore",))
    for record in running:
        with st.container(border=True):
            st.markdown(f"**{group_label(record.get('company_key'))} · {record['job']} · {record['round_number']}회차** 면접 진행 중 "
                        f"(질문 {min(record.get('q_index', 0) + 1, coach.TOTAL_QUESTIONS)}/{coach.TOTAL_QUESTIONS})")
            if st.button("이어서 하기", key=f"home_resume_{record['round_id']}"):
                load_round(record["round_id"])
                state.page = "interview"
                st.rerun()
    done = [r for r in rounds if r.get("stage") == "done"]
    if done:
        st.subheader("최근 면접")
        for record in sorted(done, key=lambda r: r.get("date", ""), reverse=True)[:5]:
            first, latest = round_totals(record)
            score = f" · 최신 종합 {latest}/{coach.TOTAL_MAX}" if latest is not None else ""
            if st.button(f"{group_label(record.get('company_key'))} · {record['job']} · {round_label(record)}{score}",
                         key=f"home_round_{record['round_id']}", width="stretch"):
                open_round(record["round_id"], LNB_EVAL)
                st.rerun()
    elif not rounds:
        st.info("아직 면접 기록이 없어요. '새 면접 시작' 으로 첫 면접을 하거나, 받아 둔 기록 파일을 'Markdown 복원' 에서 올려 주세요.")


# ── 면접 정보 설정 (파란 흐름) ─────────────────────────────────────
def job_fields(bank: pd.DataFrame, job: str) -> list[str]:
    """이 직군에 분야 질문이 있는 분야 (분야별 면접은 공통 2 + 분야 3 이라 분야 질문이 있어야 고를 수 있다)."""
    have = set(bank[(bank["직군"] == job) & (bank["분야"] != coach.DEFAULT_FIELD)]["분야"])
    return [f for f in FIELDS if f in have]


def show_interviewer(job: str):
    """직군 대표 면접관 소개 (자동 배정 · 고르지 않는다). 평가는 면접이 끝난 뒤 위원 4명이 따로 한다."""
    ptype = (coach.persona_type_names(job) or [None])[0]
    lines = coach.persona_lines(job, ptype)
    with st.container(key="persona_head"):
        st.markdown(f":material/support_agent: **{ptype or job + ' 면접관'}** · {lines[0]}" if lines else f"**{job} 면접관**")
        st.caption(f":material/forum: 면접관 1명이 질문 5개를 진행하고, 답이 부족하면 꼬리 질문을 한 번 더 해요 (질문마다 {coach.MAX_FOLLOW_UPS}개까지). "
                   "면접 중에는 평가 · 코칭을 하지 않고, 끝난 뒤 위원 4명이 평가해요.")
    card = PERSONA_CARDS.get(job, {}).get(ptype)
    if not card and lines[1:]:
        st.caption("  \n".join(lines[1:]))
    if card:
        left_titles = [t for t in ("성격", "주목하는 인재상") if t in card]
        right_titles = [t for t in card if t not in left_titles]
        with st.container(key="persona_cards"):
            for row, pair in enumerate(itertools.zip_longest(left_titles, right_titles)):
                for side, (column, title) in enumerate(zip(st.columns(2, gap="small"), pair)):
                    if title:
                        with column.container(key=f"persona_card_{row}{side}"):
                            st.markdown(f"**{title}**\n" + "\n".join(f"- {item}" for item in card[title]))


def page_setup():
    st.title("면접 정보 설정")
    try:
        bank = coach.load_questions()
    except (OSError, ValueError, KeyError):
        st.error("질문 은행(data/questions.csv)을 읽지 못했어요.")
        return
    known = sorted({r["company_key"] for r in all_rounds() if r.get("company_key")})
    company = st.text_input("회사 이름 (선택)", key="f_company", max_chars=MAX_COMPANY_CHARS,
                            placeholder="비워 두면 '기타' 그룹에 기록돼요",
                            help="같은 회사는 앞뒤 공백만 뺀 이름이 정확히 같은지로 판단해요.")
    if known:
        st.caption("기록이 있는 회사: " + " · ".join(known))
    company_desc = st.text_input("회사 설명 (선택)", key="f_company_desc", max_chars=MAX_COMPANY_DESC_CHARS,
                                 placeholder="예시: IT, 헬스케어 진단 서비스")
    if state.get("f_job") not in coach.JOBS:
        state.f_job = coach.JOBS[0] if "디자인" not in coach.JOBS else "디자인"
    job = st.pills("직군", coach.JOBS, key="f_job", required=True)
    fields = job_fields(bank, job)
    types = ["common", "field"] if fields else ["common"]
    if state.get("f_type") not in types:
        state.f_type = "common"
    itype = st.radio("면접 유형", types, key="f_type", format_func=coach.INTERVIEW_TYPES.get, horizontal=True,
                     help="공통 면접: 공통 질문 5개 · 분야별 면접: 공통 2개 + 고른 분야 3개. 회차 번호는 함께 이어져요.")
    if not fields:
        st.caption(f"'{job}' 직군은 아직 분야 질문이 없어서 공통 면접만 할 수 있어요.")
    field = coach.DEFAULT_FIELD
    if itype == "field":
        if state.get("f_field") not in fields:
            state.f_field = fields[0]
        field = st.pills("분야", fields, key="f_field", required=True)
        st.caption(f"{field} · {FIELDS[field]}")
    show_interviewer(job)
    experience = st.text_area("내 경험 (선택)", key="f_experience", height=140, max_chars=coach.MAX_EXPERIENCE_CHARS,
                              placeholder="면접관이 질문할 때 참고할 경험을 적어 주세요. 비워 둬도 면접을 시작할 수 있어요.",
                              help="면접관의 질문에만 참고해요. 평가는 실제로 제출한 답변으로만 해요.")

    key = coach.company_key(company)
    group = coach.group_rounds(all_rounds(), key, job)
    number = coach.next_round_number(all_rounds(), key, job)
    mode, source = "new", None
    if group:
        st.info(f":material/history: **{group_label(key)} · {job}** 기록 {len(group)}회차가 있어요. 이번 면접은 **{number}회차**예요.")
        mode = st.radio("질문 출제 방식", list(SETUP_MODES), key="f_mode", format_func=SETUP_MODES.get,
                        help="새로운 문제만: 이 회사 · 직군에서 안 나온 질문부터 · 섞어서: 지난 회차 질문 2개 + 새 질문 · "
                             "똑같은 질문: 이전 회차 질문 그대로 또는 과거 질문에서 무작위로.")
        if mode == "same":
            source = same_question_source(group, itype, field)
            if source is None:
                return
    else:
        st.caption(f":material/flag: **{group_label(key)} · {job}** 의 첫 회차예요 ({number}회차).")
    if st.button("새로운 회차 시작하기" if group else "면접 시작하기", type="primary", key="setup_start"):
        start_interview(bank, company, company_desc, job, field, experience, mode, source, group)


MAX_COMPANY_CHARS = 40
MAX_COMPANY_DESC_CHARS = 100
SETUP_MODES = {"new": "새로운 문제만", "mix": "섞어서", "same": "똑같은 질문"}


def same_question_source(group: list[dict], itype: str, field: str):
    """'똑같은 질문': 같은 유형(분야별이면 분야도 같은) 이전 회차 선택 / 과거 출제 질문에서 무작위 구성.
    조건이 안 되는 방법은 고를 수 없다고 알려 준다 (버튼을 끄지 않고 안내)."""
    same_kind = [r for r in group if r.get("interview_type") == itype and (itype == "common" or r.get("field") == field)
                 and len(r.get("questions") or []) == coach.TOTAL_QUESTIONS]
    past = {q["question"]: q for r in group for q in r.get("questions") or []}
    common_pool = [q for q in past.values() if q.get("field", coach.DEFAULT_FIELD) == coach.DEFAULT_FIELD]
    field_pool = [q for q in past.values() if q.get("field") == field]
    ready = coach.random_past_ready(itype, common_pool, field_pool)
    how = st.radio("똑같은 질문 구성", ["round", "random"], key="f_same_how", horizontal=True,
                   format_func={"round": "이전 회차 선택", "random": "과거 출제 질문에서 무작위"}.get)
    if how == "round":
        if not same_kind:
            st.info("같은 유형 · 분야의 이전 회차가 없어요. 다른 출제 방식을 골라 주세요.")
            return None
        ids = [r["round_id"] for r in same_kind]
        labels = {r["round_id"]: round_label(r) for r in same_kind}
        picked = st.selectbox("이전 회차", ids, index=len(ids) - 1, key="f_same_round", format_func=labels.get)
        return ("round", next(r for r in same_kind if r["round_id"] == picked))
    if not ready:
        need = "서로 다른 공통 질문 5개" if itype == "common" else "서로 다른 공통 질문 2개 + 이 분야 질문 3개"
        st.info(f"과거 질문에서 무작위로 만들려면 {need} 이상이 나온 기록이 필요해요.")
        return None
    return ("random", (common_pool, field_pool))


def start_interview(bank, company, company_desc, job, field, experience, mode, source, group):
    """면접 시작: 질문 5개를 정하고 새 회차를 만든다 (회사 · 직군의 기존 회차는 그대로)."""
    company_text = f"{company} {company_desc}"
    asked = {q["question"] for r in group for q in r.get("questions") or []}  # 이 회사 · 직군에서 나온 질문만
    note = None
    if mode == "same" and source and source[0] == "round":
        questions = [dict(q) for q in source[1]["questions"]]
    elif mode == "same" and source:
        questions = coach.random_past_questions(*source[1], interview_type_of_field(field))
    else:
        last = group[-1]["questions"] if group else None
        questions, note = coach.plan_questions(bank, job, field, company_text, mode if group else "new",
                                               [q["question"] for q in last] if last else None, asked)
    record = coach.new_round(all_rounds(), company_name=company, company_desc=company_desc, job=job, field=field,
                             question_mode=mode if group else "new", nickname=state.nickname, experience=experience,
                             questions=questions, day=user_now().date())
    record["messages"] = [{"role": "assistant", "content": f"{state.nickname} 님, 면접을 시작하겠습니다."},
                          question_message(0, questions)]
    state.store_rounds.append(record)
    load_round(record["round_id"])
    if note:
        state.notice = note
    state.page = "interview"
    st.rerun()


def interview_type_of_field(field: str) -> str:
    return coach.interview_type_of(field)


# ── 면접 진행 (5문항) ─────────────────────────────────────────────
@st.dialog("처음부터 다시 할까요?")
def restart_dialog():
    """상태창 '처음부터 다시': 진행 중인 회차의 답을 지우고 같은 회사 · 직군으로 면접 정보 설정부터.
    끝난 회차는 지우지 않고, 같은 설정으로 새 회차를 시작한다."""
    record = active_round()
    running = record is not None and record.get("stage") == "interview"
    st.warning("지금 면접의 답이 사라지고, 면접 정보 설정부터 다시 시작해요." if running
               else "이 회차 기록은 그대로 두고, 같은 회사 · 직군으로 새 회차를 시작해요.")
    stay_col, go_col = st.columns(2)
    if stay_col.button("머무르기", key="restart_stay", width="stretch"):
        st.rerun()
    if go_col.button("다시 시작하기", key="restart_go", type="primary", width="stretch"):
        if record is not None:
            if running:
                state.store_rounds.remove(record)
                state.active_round_id = None
            open_setup(record.get("company_name") or "", record["job"], record.get("company_desc") or "")
            state.f_experience = record.get("experience") or ""
        st.rerun()


def show_status_sidebar(record: dict):
    """상태창 (CLAUDE.md 화면 규칙): 질문 n/5 · 면접관이 본 이해도 · 처음부터 다시."""
    with st.sidebar:
        st.header("상태창")
        st.markdown(f"**{group_label(record.get('company_key'))} · {record['job']} · {record['round_number']}회차**")
        st.caption(f"{coach.INTERVIEW_TYPES[record['interview_type']]} · {record['field']} 분야")
        answered = state.q_index
        st.progress(answered / coach.TOTAL_QUESTIONS,
                    text=f"질문 {min(answered + 1, coach.TOTAL_QUESTIONS)}/{coach.TOTAL_QUESTIONS}")
        st.metric("면접관이 본 이해도", "-" if state.understanding is None else f"{state.understanding}/100")
        if state.get("evaluation"):
            totals = coach.total_scores(state.evaluation, state.get("retries", {}))
            st.metric("종합 점수", f"{totals['latest']}/{coach.TOTAL_MAX}", delta=totals["diff"] or None,
                      help="재도전한 질문은 같은 회차 · 질문의 최고 점수로 바꿔 넣은 합이에요.")
            st.metric("위원 평균", f"{state.evaluation['panel_average']:.1f}/{coach.PANEL_MAX}")
        if st.button(":material/restart_alt: 처음부터 다시", key="nav_restart", width="stretch"):
            state.restart_pending = True  # 확인 창은 본문에서 연다 (사이드바 안에서는 열지 않는다)
            st.rerun()


def go_round_record():
    """[평가 확인하기] → 그 회사 · 직군 · 회차의 면접 기록 확인 화면 (LNB 면접 기록 (전체) 에서 이 회차를 고른 상태)."""
    record = active_round()
    open_group(record.get("company_key"), record["job"], LNB_RECORDS)
    state.records_round = record["round_id"]


def page_interview():
    global live
    record = active_round()
    if record is None or record.get("stage") == "summary":
        st.info("진행 중인 면접이 없어요. '새 면접 시작' 으로 시작해 주세요.")
        return
    st.title(f"{group_label(record.get('company_key'))} · {record['job']} 신입 면접 · {record['round_number']}회차")
    st.caption(f"{coach.INTERVIEW_TYPES[record['interview_type']]} · {coach.field_of(profile)} 분야 · "
               f"{coach.persona_summary(record['job'])}")
    show_messages()
    live = st.container()  # 답을 보내는 동안의 내 답 · 로딩 · 에러가 대화 바로 아래에 나온다
    if state.stage == "done":
        show_interview_done()
        return
    interview_turn()


def start_evaluation():
    state.eval_running = True


def show_interview_done():
    """면접 완료 안내 → [평가 받기] → (평가 중) → [평가 확인하기].
    면접 중에는 입력창(st.chat_input) 때문에 Streamlit 이 화면을 맨 아래에 붙여 두는데, 마지막 답으로 입력창이 사라지면
    스크롤 칸이 바뀌면서 맨 위로 간다. 그래서 마지막 답 직후 한 번만 이 안내를 화면에 보이게 내린다 (finish_scroll).
    평가 중에는 [평가 받기] 를 그리지 않아 두 번 누를 수 없다. 평가 중 다른 버튼을 눌러 실행이 끊겨도 다시 부르지 않는다."""
    answered = sum(1 for m in state.messages if m.get("role") == "user")
    with st.container(key="interview_done"):
        st.markdown(f"**:material/task_alt: 질문 {coach.TOTAL_QUESTIONS}개를 모두 마쳤어요. 수고하셨습니다.**")
        if state.evaluation:
            st.caption("평가가 끝났어요. 이 회차의 면접 기록에서 위원 4명의 평가를 확인해 주세요.")
            st.button(":material/bar_chart: 평가 확인하기", type="primary", key="eval_check", on_click=go_round_record)
        else:
            if state.pop("eval_running", False) and request_evaluation():  # 깃발을 먼저 내려 끊겨도 다시 부르지 않는다
                st.rerun()
            st.caption(f"답변 {answered}개를 기록했어요. [평가 받기] 를 누르면 위원 4명이 답변을 평가해요.")
            st.button(":material/gavel: 평가 받기", type="primary", key="eval_request", on_click=start_evaluation)
    if state.pop("finish_scroll", False):
        scroll_to_key("interview_done")


# ── GNB 2 · 면접 코칭 ────────────────────────────────────────────
def page_coaching():
    group = state.get("coach_group")
    if not group or not coach.group_rounds(all_rounds(), group["key"], group["job"]):
        show_company_list()
        return
    key, job = group["key"], group["job"]
    rounds = coach.group_rounds(all_rounds(), key, job)
    head_col, back_col = st.columns([4, 1], vertical_alignment="center")
    head_col.title(f"{group_label(key)} · {job}")
    if back_col.button(":material/list: 면접 데이터 목록", key="back_to_list", width="stretch"):
        state.coach_group = None
        st.rerun()
    if "lnb_target" in state:  # open_group 이 정한 탭 (LNB 를 그리기 전에만 키를 바꿀 수 있다)
        state.lnb = state.pop("lnb_target")
    if state.get("lnb") not in LNBS:  # GNB 로 다시 들어오면 위젯 키가 지워져 있다 → 마지막에 고른 탭
        state.lnb = state.get("lnb_choice") if state.get("lnb_choice") in LNBS else LNB_RECORDS
    lnb = st.segmented_control("면접 상세", LNBS, key="lnb", required=True, label_visibility="collapsed", width="stretch")
    state.lnb_choice = lnb  # 다른 화면에 다녀와도 고른 탭을 기억 (위젯 키는 화면에서 빠지면 지워진다)
    if lnb == LNB_RECORDS:
        show_records(rounds)
    elif lnb == LNB_EVAL:
        show_eval_records(rounds)
    else:
        show_retry_all(rounds)


def show_company_list():
    """면접 데이터 목록 → 회사별 데이터 선택. 회사(또는 '기타') 아래 직군별로 회차 수를 보여 준다."""
    st.title("면접 데이터 목록")
    rounds = all_rounds()
    if not rounds:
        st.info("아직 면접 기록이 없어요. '새 면접 시작' 이나 'Markdown 복원' 으로 기록을 만들어 주세요.")
        return
    companies = sorted({r.get("company_key") for r in rounds}, key=lambda k: (k is None, k or ""))
    for key in companies:
        with st.container(border=True):
            st.markdown(f"**:material/business: {group_label(key)}**" + (" :gray[(회사 미지정)]" if key is None else ""))
            jobs = sorted({r["job"] for r in rounds if r.get("company_key") == key})
            for job in jobs:
                group = coach.group_rounds(rounds, key, job)
                latest = group[-1]
                if st.button(f"{job} · {len(group)}회차 · 최근 {latest.get('date', '')} · {coach.round_status(latest)}",
                             key=f"open_{key}_{job}", width="stretch"):
                    open_group(key, job)
                    st.rerun()


def show_records(rounds: list[dict]):
    """LNB 1 · 면접 기록 (전체): 회차별 면접 기록 확인 · 전체 회차 종합 (공통/분야) · 전체 회차 진행도 (공통/분야)."""
    st.subheader(":material/list_alt: 회차별 면접 기록")
    table = []
    for r in rounds:
        first, latest = round_totals(r)
        table.append({"회차": f"{r['round_number']}회차", "날짜": r.get("date", ""),
                      "유형": coach.INTERVIEW_TYPES[r.get("interview_type", "common")], "분야": r.get("field", ""),
                      "상태": coach.round_status(r), "최초 종합": "-" if first is None else first,
                      "최신 종합": "-" if latest is None else latest})
    st.dataframe(table, hide_index=True, width="stretch")
    ids = [r["round_id"] for r in rounds]
    labels = {r["round_id"]: round_label(r) for r in rounds}
    if state.get("records_round") not in ids:
        state.records_round = state.active_round_id if state.get("active_round_id") in ids else ids[-1]
    picked = find_round(st.selectbox("확인할 회차", ids, key="records_round", format_func=labels.get))
    with st.container(border=True):
        st.markdown(f"**{round_label(picked)}**")
        if picked.get("stage") == "summary":
            st.caption("결과 데이터 저장 기능 전에 받은 옛 리포트라 질문과 점수만 있어요.")
            for i, q in enumerate(picked["questions"]):
                scores = (picked.get("summary") or {}).get("scores") or []
                st.markdown(f"**질문 {i + 1}.** {q['question']}" + (f" · {scores[i]}점" if i < len(scores) else ""))
        else:
            for message in picked.get("messages") or []:
                with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
                    st.markdown(message["content"])
        with st.container(horizontal=True, gap="small"):
            if picked.get("stage") == "interview":
                if st.button(":material/play_arrow: 면접 이어서 하기", key="records_resume", type="primary"):
                    load_round(picked["round_id"])
                    state.page = "interview"
                    st.rerun()
            elif picked.get("stage") == "done":
                label = ":material/bar_chart: 평가 기록 보기" if picked.get("evaluation") else ":material/gavel: 평가 받으러 가기"
                if st.button(label, key="records_eval", type="primary"):
                    open_round(picked["round_id"], LNB_EVAL)
                    st.rerun()
    st.divider()
    show_overview(rounds)


def pick_round(rounds: list[dict], key: str, allowed) -> dict | None:
    """회차 고르기 (평가 기록 · 재도전). 고르면 그 회차를 화면 상태로 펼친다."""
    options = [r["round_id"] for r in rounds if allowed(r)]
    if not options:
        return None
    if state.get("active_round_id") not in options:
        load_round(options[-1])
    labels = {r["round_id"]: round_label(r) for r in rounds}
    state[key] = state.active_round_id  # 그리기 전에만 값을 정할 수 있다

    def changed():
        load_round(state[key])

    st.selectbox("회차", options, key=key, format_func=labels.get, on_change=changed)
    return active_round()


def show_eval_records(rounds: list[dict]):
    """LNB 2 · 평가 기록 (회차별): 모의 결과 확인 · 위원별 평가 확인 · 답변별 평가 확인 (퀘스트 · 경험 카드 초안은 2차 MVP)."""
    record = pick_round(rounds, "eval_round_pick", lambda r: r.get("stage") == "done")
    if record is None:
        st.info("평가할 수 있는 회차가 없어요. 질문 5개를 마친 회차가 생기면 여기서 평가 기록을 봐요.")
        return
    ev = state.evaluation
    if not ev:
        st.info("이 회차는 아직 평가 전이에요. 위원 4명에게 평가받아 주세요.")
        if st.button(":material/gavel: 평가 받기", type="primary", key="eval_request_lnb"):
            if request_evaluation():
                st.rerun()
        return
    st.subheader(":material/mail: 모의 결과")
    show_verdict(ev)
    st.divider()
    show_evaluation(ev)


def show_retry_all(rounds: list[dict]):
    """LNB 3 · 재도전 (전체): 전체 답변별 점수 · 변화 → 답변 골라 재도전 · 이전 답과 개선 답 비교 (횟수 제한 없음)."""
    evaluated = [r for r in rounds if r.get("evaluation")]
    if not evaluated:
        st.info("평가받은 회차가 생기면 답변별로 재도전할 수 있어요.")
        return
    st.subheader(":material/table_chart: 전체 답변별 점수 · 변화")
    table = []
    for r in evaluated:
        latest = {a["no"]: a for a in coach.latest_answers(r["evaluation"], r.get("retries") or {})}
        for a in r["evaluation"]["answers"]:
            now = latest[a["no"]]["score"]
            table.append({"회차": f"{r['round_number']}회차", "질문": f"{a['no']}. {a['question']}", "최초": a["score"],
                          "최고 (반영)": now, "변화": f"{now - a['score']:+d}",
                          "재도전": len((r.get("retry_history") or {}).get(a["no"], []))})
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("최고 (반영)은 같은 회차 · 질문에서 최초 점수보다 높은 재도전 중 가장 높은 점수예요. 재도전은 횟수 제한이 없어요.")
    record = pick_round(rounds, "retry_round_pick", lambda r: bool(r.get("evaluation")))
    st.divider()
    show_retry(state.evaluation)


# ── 기존 데이터 Markdown 복원 ────────────────────────────────────
def import_text(name: str, text: str) -> dict:
    """올린 파일 하나를 보관함에 더한다. 이미 있는 회차(같은 round_id)는 건너뛰고 덮어쓰지 않는다. 파일은 바꾸지 않는다."""
    try:
        parsed = coach.parse_store_file(text, coach.load_questions())
    except ValueError as e:
        error_log.record_error("restore_parse", "restore", session_id=error_session_id())
        return {"error": f"{name}: {e}"}
    except (OSError, KeyError):
        return {"error": f"{name}: 질문 은행(data/questions.csv)을 읽지 못했어요."}
    was_saved = not unsaved()
    added, skipped, warnings = 0, 0, []
    for record, problems in parsed["rounds"]:
        if find_round(record["round_id"]):
            skipped += 1
            continue
        state.store_rounds.append(record)
        added += 1
        warnings += [w for w in report_restore_problems(problems) if w not in warnings]
    if was_saved and added:  # 올린 파일에 이미 있는 기록이라 '저장 안 된 변경' 으로 보지 않는다
        state.saved_fingerprint = coach.store_fingerprint(all_rounds(), state.nickname)
    return {"name": name, "version": parsed["version"], "added": added, "skipped": skipped, "warnings": warnings}


def page_restore():
    st.title("기존 데이터 Markdown 복원")
    st.caption("이 앱에서 받은 면접 기록 파일(.md)을 올려 주세요. 통합 저장 파일(v2)과 예전 면접리포트(v1) 모두 읽어요. "
               "올린 파일은 바꾸지 않고, 이미 불러온 회차는 다시 넣지 않아요.")
    files = st.file_uploader("면접 기록 올리기", type=["md"], accept_multiple_files=True, key="restore_files",
                             label_visibility="collapsed")
    results = state.setdefault("restore_results", {})
    for f in files or []:
        if f.file_id not in results:
            results[f.file_id] = import_text(f.name, f.getvalue().decode("utf-8", errors="replace"))
    shown = [results[f.file_id] for f in files or [] if f.file_id in results]
    for result in shown:
        if "error" in result:
            st.error(result["error"])
            continue
        kind = "통합 저장(v2)" if result["version"] == 2 else "예전 면접리포트(v1)"
        st.success(f"{result['name']} · {kind} · 회차 {result['added']}개를 불러왔어요."
                   + (f" 이미 있던 회차 {result['skipped']}개는 건너뛰었어요." if result["skipped"] else ""))
        for warning in result["warnings"]:
            st.warning(warning)
    if any("error" not in r and r["added"] for r in shown):
        st.button(":material/forum: 면접 기록 보기", type="primary", key="restore_open", on_click=go_page, args=("coaching",))
    if DEV_MOCK:  # 개발용: .env 에 DEV_MOCK=1 일 때만. AI를 부르지 않고 만점 모의 회차를 넣는다
        if st.button(":material/science: 모의 데이터로 열기 (개발용 · 만점)", key="restore_mock"):
            try:
                record, problems = coach.record_from_mock(coach.load_mock(), coach.load_questions())
            except (OSError, ValueError, KeyError) as e:
                st.error(f"모의 데이터를 읽지 못했어요. {e}")
            else:
                if not find_round(record["round_id"]):
                    state.store_rounds.append(record)
                state.notice_warnings = report_restore_problems(problems)
                state.notice = "개발용 모의 데이터(만점)를 열었어요. 글은 모두 예시예요."
                open_round(record["round_id"], LNB_EVAL)
                st.rerun()


# ── 화면 흐름 ────────────────────────────────────────────────
sync_active()
profile = coach.round_profile(active_round()) if active_round() else None
if state.get("go_tab"):  # 화면 함수가 고른 LNB 로 (그리기 전에 정한다)
    target = state.pop("go_tab")
    if active_round():
        open_group(active_round().get("company_key"), active_round()["job"], target)
if state.get("go_retry_no"):
    state.retry_no = state.pop("go_retry_no")
if state.pop("open_next_round", False) and active_round():  # 모의 결과의 '분야를 골라 다음 회차'
    record = active_round()
    open_setup(record.get("company_name") or "", record["job"], record.get("company_desc") or "")
    state.f_type = "field"

if state.page == "start":
    page_start()
    st.stop()
show_header()
if state.pop("page_top", False):
    scroll_to_top()
show_notices()
if state.pop("restart_pending", False):
    restart_dialog()
PAGES = {"home": page_home, "coaching": page_coaching, "setup": page_setup, "restore": page_restore,
         "interview": page_interview}
try:
    PAGES.get(state.page, page_home)()
finally:
    # 상태창은 페이지를 그린 뒤에 (페이지에서 회차를 고르면 그 회차로)
    if active_round() and active_round().get("stage") != "summary" and state.page in ("interview", "coaching"):
        show_status_sidebar(active_round())
