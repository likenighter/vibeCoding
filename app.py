import streamlit as st
import uuid
import json
import os
from datetime import datetime
from pypdf import PdfReader
from openai import OpenAI
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def apply_pastel_blue_theme():
    """앱 전체에 부드러운 파스텔 블루 디자인을 적용합니다."""
    st.markdown(
        """
        <style>
        :root {
            --sky: #dceeff;
            --sky-deep: #b8dbf7;
            --navy: #33495e;
            --muted: #718295;
            --surface: #ffffff;
            --line: #e5edf4;
            --action: #2f80ed;
            --action-dark: #1f68c7;
            --soft-action: #e7f2ff;
        }

        .stApp {
            background: linear-gradient(180deg, var(--sky) 0%, #eef7ff 48%, #f8fbfe 100%);
            color: var(--navy);
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.72);
            border-right: 1px solid var(--sky-deep);
            box-shadow: 4px 0 20px rgba(51, 73, 94, 0.06);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] label {
            color: var(--navy);
        }

        h1, h2, h3, h4, h5 {
            color: var(--navy);
            letter-spacing: 0;
        }

        [data-testid="stAppViewContainer"] > .main {
            max-width: 920px;
            margin: 0 auto;
        }

        div[data-testid="stForm"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1.25rem;
            box-shadow: 0 12px 30px rgba(51, 73, 94, 0.08);
        }

        div[data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(51, 73, 94, 0.05);
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stFileUploader"] section {
            background: #fbfdff;
            border-color: var(--sky-deep);
            border-radius: 10px;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: var(--action);
            box-shadow: 0 0 0 2px rgba(47, 128, 237, 0.18);
        }

        .stButton > button,
        .stFormSubmitButton > button {
            background: var(--action);
            color: #ffffff;
            border: 1px solid var(--action);
            border-radius: 9px;
            font-weight: 600;
            transition: background 0.2s ease, transform 0.2s ease;
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: var(--action-dark);
            border-color: var(--action-dark);
            transform: translateY(-1px);
        }

        div[data-testid="stAlert"] {
            border-radius: 10px;
        }

        div[data-baseweb="tab-list"] {
            gap: 6px;
            border-bottom: 1px solid var(--line);
        }

        button[data-baseweb="tab"] {
            color: var(--muted);
            border-radius: 9px 9px 0 0;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--action-dark);
            background: var(--soft-action);
        }

        hr {
            border-color: var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

@st.cache_resource
def get_supabase_client():
    """secrets.toml의 Supabase 설정으로 클라이언트를 생성합니다."""
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as error:
        st.error(f"Supabase 연결 설정을 확인해주세요: {error}")
        return None

def fetch_app_name(table_name, default_name):
    """이름 테이블의 첫 번째 이름을 조회하고, 없으면 기본 이름을 생성합니다."""
    client = get_supabase_client()
    if client is None:
        return None
    try:
        response = client.table(table_name).select("id, name").order(
            "id", desc=False
        ).limit(1).execute()
        data = response.data or []
        if data:
            return data[0]

        response = client.table(table_name).insert({"name": default_name}).execute()
        data = response.data or []
        return data[0] if data else None
    except Exception as error:
        st.error(f"{table_name} 테이블의 이름을 불러오는 중 오류가 발생했습니다: {error}")
        return None

def update_app_name(table_name, new_name):
    """이름 테이블의 첫 번째 행을 새 이름으로 변경합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        response = client.table(table_name).select("id").order(
            "id", desc=False
        ).limit(1).execute()
        data = response.data or []
        if data:
            client.table(table_name).update({"name": new_name.strip()}).eq(
                "id", data[0]["id"]
            ).execute()
        else:
            client.table(table_name).insert({"name": new_name.strip()}).execute()
        return True
    except Exception as error:
        st.error(f"{table_name} 테이블의 이름을 저장하는 중 오류가 발생했습니다: {error}")
        return False

def load_app_names():
    """Supabase의 메모장·튜터 이름을 세션 상태에 반영합니다."""
    memo_record = fetch_app_name("memo_name", st.session_state.memo_name)
    tutor_record = fetch_app_name("tutor_name", st.session_state.tutor_name)
    if memo_record and memo_record.get("name"):
        st.session_state.memo_name = memo_record["name"]
    if tutor_record and tutor_record.get("name"):
        st.session_state.tutor_name = tutor_record["name"]

def fetch_memos():
    """Supabase memos 테이블에서 최신 메모를 조회합니다."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        response = client.table("memos").select("id, content, created_at").order(
            "created_at", desc=True
        ).execute()
        return response.data or []
    except Exception as error:
        st.error(f"메모를 불러오는 중 오류가 발생했습니다: {error}")
        return []

def insert_memo(content):
    """메모 내용을 Supabase memos 테이블에 저장합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("memos").insert({"content": content.strip()}).execute()
        return True
    except Exception as error:
        st.error(f"메모 저장 중 오류가 발생했습니다: {error}")
        return False

def delete_memo(memo_id):
    """Supabase memos 테이블에서 메모를 실제로 삭제합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("memos").delete().eq("id", memo_id).execute()
        return True
    except Exception as error:
        st.error(f"메모 삭제 중 오류가 발생했습니다: {error}")
        return False

def insert_tutor_session(header, summary, quiz):
    """요약과 퀴즈를 tutor_sessions에 저장하고 새 세션 ID를 반환합니다."""
    client = get_supabase_client()
    if client is None:
        return None
    try:
        response = client.table("tutor_sessions").insert({
            "header": header.strip(),
            "summary": summary,
            "quiz": quiz,
            "chat_history": [],
            "review": [],
        }).execute()
        data = response.data or []
        if not data:
            st.error("튜터 세션 저장 결과가 비어 있습니다.")
            return None
        return data[0]["id"]
    except Exception as error:
        st.error(f"튜터 세션 저장 중 오류가 발생했습니다: {error}")
        return None

def fetch_tutor_session(session_id):
    """session_id로 tutor_sessions의 요약·퀴즈·대화를 조회합니다."""
    client = get_supabase_client()
    if client is None:
        return None
    try:
        response = client.table("tutor_sessions").select(
            "id, header, summary, quiz, chat_history, review, created_at"
        ).eq("id", session_id).limit(1).execute()
        data = response.data or []
        return data[0] if data else None
    except Exception as error:
        st.error(f"튜터 세션을 불러오는 중 오류가 발생했습니다: {error}")
        return None

def fetch_tutor_sessions():
    """tutor_sessions에서 세션 목록을 최신순으로 조회합니다."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        response = client.table("tutor_sessions").select(
            "id, header, summary, created_at"
        ).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as error:
        st.error(f"튜터 세션 목록을 불러오는 중 오류가 발생했습니다: {error}")
        return []

def update_tutor_chat_history(session_id, chat_history):
    """튜터 세션의 최신 대화 기록을 Supabase에 반영합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("tutor_sessions").update({
            "chat_history": chat_history,
        }).eq("id", session_id).execute()
        return True
    except Exception as error:
        st.error(f"대화 기록 저장 중 오류가 발생했습니다: {error}")
        return False

def update_tutor_review(session_id, review):
    """튜터 세션의 틀린 문제 복습 내용을 Supabase에 저장합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("tutor_sessions").update({
            "review": review,
        }).eq("id", session_id).execute()
        return True
    except Exception as error:
        st.error(f"복습 내용 저장 중 오류가 발생했습니다: {error}")
        return False

def update_tutor_header(session_id, header):
    """tutor_sessions의 튜터 이름을 변경합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("tutor_sessions").update({"header": header.strip()}).eq(
            "id", session_id
        ).execute()
        return True
    except Exception as error:
        st.error(f"튜터 이름 변경 중 오류가 발생했습니다: {error}")
        return False

def delete_tutor_session(session_id):
    """tutor_sessions에서 선택한 튜터 세션을 삭제합니다."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("tutor_sessions").delete().eq("id", session_id).execute()
        return True
    except Exception as error:
        st.error(f"튜터 세션 삭제 중 오류가 발생했습니다: {error}")
        return False

# --- OpenAI 요약 함수 ---

def build_summary_system_prompt():
    """OpenAI가 반환할 요약 JSON 형식의 시스템 프롬프트를 생성합니다."""
    return (
        "당신은 전문 문서 분석가입니다. 제공된 텍스트를 분석하여 "
        "반드시 아래의 JSON 형식으로만 응답해주세요 (다른 부가 설명 없이):\n"
        "{\n"
        '  "summary": ["핵심 요약 1문장", "핵심 요약 2문장", "핵심 요약 3문장"],\n'
        '  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],\n'
        '  "difficulty": "상/중/하 중 하나"\n'
        "}"
    )

def summarize_pdf_text(full_text):
    """OpenAI API를 사용하여 PDF 텍스트를 요약하고 JSON으로 반환합니다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        return {"error": "OPENAI_API_KEY가 설정되지 않았습니다. 환경 변수나 st.secrets를 확인해주세요."}

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": build_summary_system_prompt()},
                {"role": "user", "content": f"다음 텍스트를 요약해 주세요:\n\n{full_text}"},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"API 호출 중 오류가 발생했습니다: {e}"}

QUIZ_SYSTEM_PROMPT = """
당신은 학습 퀴즈를 만드는 도우미입니다.
주어진 요약을 바탕으로 4지선다 퀴즈 3문항을 만드세요.
각 문항은 question, options(4개), answer(정답 인덱스, 0부터 시작), explanation을 포함해야 합니다.
결과는 {"questions": [...]} 형태의 JSON으로 반환하세요.
"""

def generate_quiz_from_summary(summary_data):
    """PDF 원문이 아닌 저장된 요약 텍스트만 사용해 퀴즈 JSON을 생성합니다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        return {"error": "OPENAI_API_KEY가 설정되지 않았습니다. 환경 변수나 st.secrets를 확인해주세요."}

    if not summary_data or "error" in summary_data:
        return {"error": "퀴즈를 만들 수 있는 요약 결과가 없습니다."}

    summary_text = " ".join(summary_data.get("summary", []))
    if not summary_text.strip():
        return {"error": "요약 텍스트가 없어 퀴즈를 만들 수 없습니다."}

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                {"role": "user", "content": f"다음 요약만 사용해 퀴즈를 만들어 주세요:\n\n{summary_text}"},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": f"퀴즈 생성 중 오류가 발생했습니다: {e}"}

def get_wrong_questions(note_id, quiz_data):
    """선택 답안과 정답을 비교해 틀린 문제만 반환합니다."""
    if not quiz_data or "questions" not in quiz_data:
        return []

    answers = st.session_state.quiz_answers.get(note_id, {})
    return [
        question
        for index, question in enumerate(quiz_data["questions"])
        if index in answers and answers[index] != question.get("answer")
    ]

def save_review_to_session(note_id, review_id, question, explanation, current_review):
    """오답 문제와 AI 설명을 tutor_sessions.review에 저장합니다."""
    review = list(current_review or [])
    if any(item.get("id") == review_id for item in review):
        return True

    review.append({
        "id": review_id,
        "question": question,
        "explanation": explanation,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return update_tutor_review(note_id, review)

def render_review_notes(note):
    """tutor_sessions.review에 저장된 틀린 문제 복습 내용을 표시합니다."""
    review_notes = note.get("review", [])
    st.markdown("##### 🔁 틀린 문제 복습")
    if not review_notes:
        st.caption("저장된 복습 내용이 없습니다.")
        return

    for index, review in enumerate(review_notes, 1):
        with st.expander(f"복습 {index}: {review.get('question', '')}", expanded=False):
            st.caption(f"저장 시각: {review.get('timestamp', '')}")
            st.write(review.get("explanation", ""))

def ask_tutor(document, question, wrong_questions=None, review_question=None, chat_history=None):
    """요약, 전체 퀴즈, 오답을 참고해 사용자의 질문에 답합니다."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            pass

    if not api_key:
        return "OPENAI_API_KEY가 설정되지 않았습니다."

    summary = document.get("summary_data", {})
    quiz = document.get("quiz_data", {})
    wrong = wrong_questions or []
    system_prompt = f"""
당신은 PDF 학습을 돕는 튜터입니다.
문서에 관해 정확하고 이해하기 쉽게 답변하세요.
반드시 아래 자료만 근거로 답변하고, 자료에 없는 내용은 모른다고 말하세요.

[문서 텍스트]
{document.get("full_text", "")}

[요약]
{json.dumps(summary, ensure_ascii=False)}

[퀴즈 전체]
{json.dumps(quiz, ensure_ascii=False)}

[현재까지 틀린 문제]
{json.dumps(wrong, ensure_ascii=False)}

[이전 대화]
{json.dumps(chat_history or [], ensure_ascii=False)}
"""
    if review_question:
        system_prompt += """

지금은 틀린 문제 복습 모드입니다. 현재 문제 하나만 짚어서
왜 정답이 맞는지, 사용자가 오답을 고를 만한 이유는 무엇인지 설명하세요.
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"질문 처리 중 오류가 발생했습니다: {e}"

# --- 함수 정의 ---

def init_session_state():
    """세션 상태를 초기화합니다."""
    if "pdf_notes" not in st.session_state:
        st.session_state.pdf_notes = []
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = {}
    if "tutor_document" not in st.session_state:
        st.session_state.tutor_document = None
    if "tutor_chat" not in st.session_state:
        st.session_state.tutor_chat = []
    if "review_index" not in st.session_state:
        st.session_state.review_index = None
    if "tutor_session_id" not in st.session_state:
        st.session_state.tutor_session_id = None
    if "tutor_pages" not in st.session_state:
        st.session_state.tutor_pages = []
    if "tutor_full_text" not in st.session_state:
        st.session_state.tutor_full_text = ""
    if "tutor_summary" not in st.session_state:
        st.session_state.tutor_summary = None
    if "tutor_quiz" not in st.session_state:
        st.session_state.tutor_quiz = None
    if "tutor_review" not in st.session_state:
        st.session_state.tutor_review = []
    if "tutor_header" not in st.session_state:
        st.session_state.tutor_header = ""
    if "last_menu" not in st.session_state:
        st.session_state.last_menu = None
    if "memo_name" not in st.session_state:
        st.session_state.memo_name = "나만의 메모장"
    if "tutor_name" not in st.session_state:
        st.session_state.tutor_name = "나만의 튜터"
    if "editing_tutor_id" not in st.session_state:
        st.session_state.editing_tutor_id = None

def restore_tutor_session():
    """URL의 session_id가 있으면 Supabase에서 튜터 세션을 복원합니다."""
    session_id = st.query_params.get("session_id")
    if not session_id or st.session_state.tutor_session_id == session_id:
        return

    session = fetch_tutor_session(session_id)
    if not session:
        st.warning("요청한 튜터 세션을 찾을 수 없습니다.")
        return

    summary = session.get("summary") or {}
    quiz = session.get("quiz") or {}
    header = session.get("header") or "이름 없는 튜터"
    review = session.get("review") or []
    chat_history = session.get("chat_history") or []
    st.session_state.tutor_session_id = str(session["id"])
    st.session_state.tutor_pages = []
    st.session_state.tutor_full_text = ""
    st.session_state.tutor_summary = summary
    st.session_state.tutor_quiz = quiz
    st.session_state.tutor_review = review
    st.session_state.tutor_header = header
    st.session_state.tutor_chat = chat_history
    st.session_state.review_index = None
    st.session_state.tutor_document = {
        "id": str(session["id"]),
        "type": "pdf",
        "header": header,
        "pdf_name": "복원된 튜터 세션",
        "pages": [],
        "full_text": "",
        "summary_data": summary,
        "quiz_data": quiz,
        "review": review,
        "timestamp": session.get("created_at", ""),
    }

def save_text_note(text):
    """일반 텍스트 메모를 Supabase에 저장합니다."""
    return insert_memo(text)

def extract_pdf_content(uploaded_file):
    """PDF의 페이지별 텍스트와 전체 텍스트를 추출합니다."""
    reader = PdfReader(uploaded_file)
    pages = []
    full_text = ""
    for index, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            clean_text = text.strip()
            pages.append({"page_num": index + 1, "text": clean_text})
            full_text += clean_text + "\n"
    return pages, full_text

def save_pdf_note(uploaded_file):
    """PDF 파일에서 텍스트를 추출하여 메모로 저장하고 요약을 생성합니다."""
    try:
        reader = PdfReader(uploaded_file)
        pages = []
        full_text = ""
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                clean_text = text.strip()
                pages.append({
                    "page_num": idx + 1,
                    "text": clean_text
                })
                full_text += clean_text + "\n"
        
        if pages:
            # OpenAI 요약 생성
            summary_data = summarize_pdf_text(full_text)

            new_note = {
                "id": str(uuid.uuid4()),
                "type": "pdf",
                "pdf_name": uploaded_file.name,
                "pages": pages,
                "summary_data": summary_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.pdf_notes.append(new_note)
            return True
    except Exception as e:
        st.error(f"PDF 파일 읽기 오류: {e}")
    return False

def render_summary(summary_data):
    """요약 JSON을 핵심 요약, 키워드, 난이도로 나누어 표시합니다."""
    if not summary_data:
        return

    with st.expander("🤖 AI 문서 요약 결과", expanded=True):
        if "error" in summary_data:
            st.error(summary_data["error"])
            return

        st.markdown("##### 📌 핵심 요약 (3문장)")
        for index, sentence in enumerate(summary_data.get("summary", []), 1):
            st.write(f"{index}. {sentence}")

        st.markdown("##### 🔑 주요 키워드 (5개)")
        keywords = summary_data.get("keywords", [])
        st.markdown(" ".join(f"`{keyword}`" for keyword in keywords))

        st.markdown("##### 📊 난이도")
        st.info(f"난이도: **{summary_data.get('difficulty', '미정')}**")

def save_quiz_answer(quiz_id, question_index, widget_key, options):
    """사용자가 선택한 퀴즈 답안을 session_state에 저장합니다."""
    selected_option = st.session_state.get(widget_key)
    if selected_option is not None:
        selected_index = options.index(selected_option)
        st.session_state.quiz_answers.setdefault(quiz_id, {})[question_index] = selected_index

def render_quiz(note_id, summary_data, quiz_data):
    """요약 기반 퀴즈를 생성하거나 문항별 선택 결과를 표시합니다."""
    if quiz_data is None:
        if st.button("📝 퀴즈 생성", key=f"generate_quiz_{note_id}"):
            with st.spinner("요약 내용을 바탕으로 퀴즈를 만드는 중입니다..."):
                quiz_data = generate_quiz_from_summary(summary_data)
                for note in st.session_state.pdf_notes:
                    if note.get("id") == note_id:
                        note["quiz_data"] = quiz_data
                        break
                st.rerun()
        return

    with st.expander("📝 요약 기반 퀴즈", expanded=True):
        if "error" in quiz_data:
            st.error(quiz_data["error"])
            return

        for question_index, question_data in enumerate(quiz_data.get("questions", [])):
            question_key = f"{note_id}_{question_index}"
            st.markdown(f"**{question_index + 1}. {question_data.get('question', '')}**")
            options = question_data.get("options", [])
            widget_key = f"quiz_choice_{question_key}"
            st.radio(
                "보기를 선택하세요",
                options,
                index=None,
                key=widget_key,
                label_visibility="collapsed",
                on_change=save_quiz_answer,
                args=(note_id, question_index, widget_key, options),
            )

            selected_index = st.session_state.quiz_answers.get(note_id, {}).get(question_index)
            if selected_index is not None:
                answer_index = question_data.get("answer")
                if selected_index == answer_index:
                    st.success("정답입니다!")
                else:
                    st.error("오답입니다.")
                st.info(f"해설: {question_data.get('explanation', '')}")

            if question_index < len(quiz_data.get("questions", [])) - 1:
                st.divider()

def delete_note(note_id):
    """지정된 ID의 메모를 삭제합니다."""
    st.session_state.pdf_notes = [n for n in st.session_state.pdf_notes if n["id"] != note_id]
    st.rerun()

def render_sidebar():
    """사이드바 메뉴를 구성합니다."""
    st.sidebar.title("📌 메뉴")
    return st.sidebar.radio(
        "원하는 기능을 선택하세요",
        ["memo", "tutor"],
        format_func=lambda menu_key: (
            st.session_state.memo_name if menu_key == "memo"
            else st.session_state.tutor_name
        ),
        key="main_menu",
    )

def render_page_header(menu):
    """메모장과 튜터의 이름을 메인 페이지에서 각각 변경합니다."""
    if menu == "memo":
        name_key = "memo_name"
        title = st.session_state.memo_name
        form_key = "memo_name_form"
        input_key = "memo_name_input"
    else:
        name_key = "tutor_name"
        title = st.session_state.tutor_name
        form_key = "tutor_name_form"
        input_key = "tutor_name_input"

    title_col, rename_col = st.columns([0.72, 0.28], vertical_alignment="bottom")
    with title_col:
        st.title(title)
    with rename_col:
        with st.form(form_key):
            new_name = st.text_input("이름", value=title, key=input_key)
            if st.form_submit_button("이름 변경"):
                if new_name.strip():
                    table_name = "memo_name" if menu == "memo" else "tutor_name"
                    if update_app_name(table_name, new_name):
                        st.session_state[name_key] = new_name.strip()
                        st.rerun()
                else:
                    st.warning("이름을 입력하세요.")

def render_note_input():
    """메모 작성 UI를 렌더링합니다."""
    st.subheader("✍️ 메모 작성")
    with st.form("memo_form", clear_on_submit=True):
        note_text = st.text_input("메모를 직접 입력하세요")
        if st.form_submit_button("저장"):
            if note_text and note_text.strip():
                if save_text_note(note_text):
                    st.rerun()
            else:
                st.warning("메모를 입력하세요.")

def render_tutor_chat(document):
    """문서, 요약, 퀴즈를 기반으로 질문하고 오답을 복습하는 채팅 UI를 렌더링합니다."""
    note_id = document["id"]
    wrong_questions = get_wrong_questions(note_id, document.get("quiz_data"))

    for message in st.session_state.tutor_chat:
        if message.get("kind") == "review":
            review_id = message["review_id"]
            saved = any(
                item.get("id") == review_id
                for item in document.get("review", [])
            )
            message_column, action_column = st.columns([0.82, 0.18])
            with message_column:
                with st.chat_message("assistant"):
                    st.write(message["content"])
            with action_column:
                if saved:
                    st.caption("저장됨")
                elif st.button("저장", key=f"save_review_{review_id}"):
                    review = {
                        "id": review_id,
                        "question": message["question"].get("question", ""),
                        "explanation": message["explanation"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    if save_review_to_session(
                        note_id,
                        review_id,
                        review["question"],
                        review["explanation"],
                        document.get("review", []),
                    ):
                        document.setdefault("review", []).append(review)
                        st.session_state.tutor_review = document["review"]
                        st.rerun()
        else:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    if wrong_questions:
        review_index = st.session_state.review_index
        if review_index is None:
            review_label = "틀린 문제 복습하기"
        elif review_index < len(wrong_questions):
            review_label = "다음 틀린 문제 복습하기"
        else:
            review_label = None

        if review_label and st.button(review_label, key=f"review_wrong_{note_id}"):
            if review_index is None:
                review_index = 0
            review_question = wrong_questions[review_index]
            with st.spinner("틀린 문제를 설명하는 중입니다..."):
                answer = ask_tutor(
                    document,
                    f"다음 틀린 문제를 복습시켜 주세요:\n{json.dumps(review_question, ensure_ascii=False)}",
                    wrong_questions,
                    review_question,
                    st.session_state.tutor_chat,
                )
            st.session_state.tutor_chat.append({
                "role": "assistant",
                "content": f"### 오답 복습 {review_index + 1}\n\n{answer}",
                "kind": "review",
                "review_id": str(uuid.uuid4()),
                "question": review_question,
                "explanation": answer,
            })
            update_tutor_chat_history(note_id, st.session_state.tutor_chat)
            st.session_state.review_index = review_index + 1
            st.rerun()

    question = st.chat_input("문서나 퀴즈에 대해 질문해 보세요")
    if question:
        st.session_state.tutor_chat.append({"role": "user", "content": question})
        with st.spinner("답변을 생성하는 중입니다..."):
            answer = ask_tutor(
                document,
                question,
                wrong_questions,
                chat_history=st.session_state.tutor_chat,
            )
        st.session_state.tutor_chat.append({"role": "assistant", "content": answer})
        update_tutor_chat_history(note_id, st.session_state.tutor_chat)
        st.rerun()

def render_tutor_tabs(document):
    """PDF 분석 결과를 요약, 퀴즈, 질문하기 하위 탭으로 렌더링합니다."""
    summary_tab, quiz_tab, chat_tab = st.tabs(["요약", "퀴즈", "질문하기"])

    with summary_tab:
        render_summary(document.get("summary_data"))
        render_review_notes(document)

    with quiz_tab:
        render_quiz(document["id"], document.get("summary_data"), document.get("quiz_data"))

    with chat_tab:
        render_tutor_chat(document)

def clear_tutor_state():
    """현재 튜터 상세 상태를 초기화합니다."""
    st.session_state.tutor_session_id = None
    st.session_state.tutor_document = None
    st.session_state.tutor_pages = []
    st.session_state.tutor_full_text = ""
    st.session_state.tutor_summary = None
    st.session_state.tutor_quiz = None
    st.session_state.tutor_review = []
    st.session_state.tutor_header = ""
    st.session_state.tutor_chat = []
    st.session_state.review_index = None

def render_tutor_session_list():
    """Supabase에서 최신 튜터 세션 목록을 조회해 표시합니다."""
    st.subheader("📚 지난 튜터 세션")
    if st.button("새 PDF로 시작하기", key="new_tutor_session"):
        clear_tutor_state()
        st.query_params.clear()
        st.query_params["tutor_view"] = "upload"
        st.rerun()

    sessions = fetch_tutor_sessions()
    if not sessions:
        st.info("저장된 튜터 세션이 없습니다.")
        return

    for session in sessions:
        header = session.get("header") or "이름 없는 튜터"
        session_id = str(session["id"])
        name_col, menu_col = st.columns([0.88, 0.12])
        with name_col:
            if st.button(header, key=f"open_tutor_{session_id}", use_container_width=True):
                clear_tutor_state()
                st.query_params.clear()
                st.query_params["session_id"] = session_id
                st.rerun()
        with menu_col:
            with st.popover("⋯", use_container_width=True):
                if st.button("삭제", key=f"delete_tutor_{session_id}", use_container_width=True):
                    if delete_tutor_session(session_id):
                        if st.session_state.tutor_session_id == session_id:
                            clear_tutor_state()
                        st.rerun()
                if st.button("이름 변경", key=f"edit_tutor_{session_id}", use_container_width=True):
                    st.session_state.editing_tutor_id = session_id
                    st.rerun()

        if st.session_state.editing_tutor_id == session_id:
            with st.form(f"tutor_rename_form_{session_id}"):
                new_header = st.text_input("새 튜터 이름", value=header)
                save_col, cancel_col = st.columns(2)
                with save_col:
                    save_name = st.form_submit_button("저장")
                with cancel_col:
                    cancel_name = st.form_submit_button("취소")
                if cancel_name:
                    st.session_state.editing_tutor_id = None
                    st.rerun()
                if save_name:
                    if not new_header.strip():
                        st.warning("튜터 이름을 입력하세요.")
                    elif update_tutor_header(session_id, new_header):
                        st.session_state.editing_tutor_id = None
                        st.rerun()

def render_tutor_upload():
    """PDF 업로드부터 텍스트 추출, 요약, 퀴즈 생성을 순서대로 실행합니다."""
    if st.button("목록으로 돌아가기", key="back_from_upload"):
        clear_tutor_state()
        st.query_params.clear()
        st.query_params["tutor_view"] = "list"
        st.rerun()

    st.subheader(f"{st.session_state.tutor_name} 만들기")
    tutor_header = st.text_input(
        "튜터의 이름을 입력하세요",
        key="tutor_header",
        placeholder="예: 한국사 시험 대비",
    )
    with st.form("pdf_form", clear_on_submit=True):
        upload_file = st.file_uploader("PDF 파일을 선택하세요", type="pdf")
        submitted = st.form_submit_button("PDF 분석 시작")

    if submitted:
        if not tutor_header.strip():
            st.warning("튜터의 이름을 입력하세요.")
        elif upload_file is None:
            st.warning("PDF 파일을 업로드하세요.")
        else:
            try:
                with st.spinner("1/3 PDF 텍스트를 페이지별로 추출하는 중입니다..."):
                    pages, full_text = extract_pdf_content(upload_file)
                if not pages:
                    st.warning("PDF에서 텍스트를 추출할 수 없습니다.")
                else:
                    with st.spinner("2/3 추출된 텍스트를 요약하는 중입니다..."):
                        summary_data = summarize_pdf_text(full_text)
                    with st.spinner("3/3 요약을 바탕으로 퀴즈를 생성하는 중입니다..."):
                        quiz_data = generate_quiz_from_summary(summary_data)

                    session_id = insert_tutor_session(tutor_header, summary_data, quiz_data)
                    if session_id is None:
                        return
                    st.query_params["session_id"] = str(session_id)

                    document = {
                        "id": str(session_id),
                        "type": "pdf",
                        "header": tutor_header.strip(),
                        "pdf_name": upload_file.name,
                        "pages": pages,
                        "full_text": full_text,
                        "summary_data": summary_data,
                        "quiz_data": quiz_data,
                        "review": [],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    st.session_state.tutor_session_id = str(session_id)
                    st.session_state.tutor_pages = pages
                    st.session_state.tutor_full_text = full_text
                    st.session_state.tutor_summary = summary_data
                    st.session_state.tutor_quiz = quiz_data
                    st.session_state.tutor_review = []
                    st.session_state.tutor_document = document
                    st.session_state.tutor_chat = []
                    st.session_state.review_index = None
                    st.rerun()
            except Exception as e:
                st.error(f"PDF 처리 중 오류가 발생했습니다: {e}")

def render_tutor_detail():
    """선택한 튜터 세션의 요약, 퀴즈, 대화를 표시합니다."""
    if st.button("목록으로 돌아가기", key="back_from_detail"):
        clear_tutor_state()
        st.query_params.clear()
        st.query_params["tutor_view"] = "list"
        st.rerun()

    if st.session_state.tutor_document:
        st.subheader(st.session_state.tutor_document.get("header", "이름 없는 튜터"))
        render_tutor_tabs(st.session_state.tutor_document)

def render_tutor_input():
    """목록, 새 업로드, 세션 상세 화면을 query param으로 라우팅합니다."""
    session_id = st.query_params.get("session_id")
    if session_id:
        if st.session_state.tutor_document is None:
            restore_tutor_session()
        render_tutor_detail()
    elif st.query_params.get("tutor_view") == "upload":
        render_tutor_upload()
    else:
        render_tutor_session_list()

def render_note_list():
    """저장된 메모 목록을 렌더링합니다."""
    st.subheader("📋 저장된 메모 목록")
    memos = fetch_memos()
    pdf_notes = st.session_state.pdf_notes
    if not memos and not pdf_notes:
        st.info("등록된 메모가 없습니다.")
        return

    for memo in memos:
        memo_id = memo["id"]
        memo_text = memo.get("content", "")
        st.write("---")
        st.caption(f"🕒 {memo.get('created_at', '')}")
        if len(memo_text) > 50:
            show_key = f"show_memo_{memo_id}"
            if show_key not in st.session_state:
                st.session_state[show_key] = False

            if st.session_state[show_key]:
                st.write(memo_text)
                if st.button("(간략히)", key=f"btn_memo_{memo_id}"):
                    st.session_state[show_key] = False
                    st.rerun()
            else:
                st.write(f"{memo_text[:50]}...")
                if st.button("더보기", key=f"btn_memo_{memo_id}"):
                    st.session_state[show_key] = True
                    st.rerun()
        else:
            st.write(memo_text)

        if st.button("삭제", key=f"delete_memo_{memo_id}"):
            if delete_memo(memo_id):
                st.rerun()

    sorted_pdf_notes = sorted(pdf_notes, key=lambda x: x["timestamp"], reverse=True)
    for note in sorted_pdf_notes:
        note_id = note["id"]
        st.write("---")
        st.caption(f"🕒 {note['timestamp']}")
        st.markdown(f"📄 **{note.get('pdf_name', 'PDF 문서')}** (총 {len(note['pages'])}페이지)")
        render_summary(note.get("summary_data"))
        render_quiz(note_id, note.get("summary_data"), note.get("quiz_data"))
        render_review_notes(note)
        if st.button("삭제", key=f"del_{note_id}"):
            delete_note(note_id)

# --- 메인 실행 ---

st.set_page_config(page_title="나만의 메모장", page_icon="📝")
apply_pastel_blue_theme()

init_session_state()
load_app_names()
restore_tutor_session()
menu = render_sidebar()

if menu == "tutor" and st.session_state.last_menu != "tutor":
    if not st.query_params.get("session_id"):
        clear_tutor_state()
        st.query_params.clear()
        st.query_params["tutor_view"] = "list"
st.session_state.last_menu = menu
render_page_header(menu)

if menu == "memo":
    render_note_input()
    render_note_list()
elif menu == "tutor":
    render_tutor_input()