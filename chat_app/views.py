from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
from django.shortcuts import render
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json 


load_dotenv()

def get_pinecone_index():
    """Pinecone 클라이언트를 초기화하고 인덱스를 반환하는 함수"""
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
    
    # 환경 변수 체크
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT or not PINECONE_INDEX_NAME:
        # Django runserver 체크 단계에서 에러가 나지 않도록 일반적인 Exception 처리
        raise EnvironmentError("필수 Pinecone 환경 변수(KEY, ENV, NAME)가 설정되지 않았습니다.")

    INDEX_DIMENSION = 1024 # 1024로 고정
    
    # 1. 클라이언트 초기화
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

    # 3. 인덱스 연결
    return pc.Index(PINECONE_INDEX_NAME)

# 초기화 함수는 별도로 호출하지 않고, 필요한 함수 내에서 호출합니다.
# OpenAI 클라이언트 초기화 (이것은 그대로 모듈 레벨에 둘 수 있습니다.)
client_openai = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-large" 

def search_documents(
    query: str, user_id: int, n_results: int = 5
    ) -> List[str]:
    """
    Pinecone에서 쿼리와 관련된 문서를 검색합니다.
    (컬렉션 이름 대신 인덱스 이름을 사용하며, 필터링 방식이 달라집니다.)
    """
    try:
        pinecone_index = get_pinecone_index() 

        PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

        print(f"'{PINECONE_INDEX_NAME}' 인덱스에서 관련 문서를 검색합니다...")
        # 1. 쿼리 임베딩 생성 (ChromaDB와 동일)
        response = client_openai.embeddings.create(
            input = [query],
            model = EMBEDDING_MODEL,
            dimensions = 1024
        )
        query_embedding = response.data[0].embedding

        # ChromaDB의 컬렉션 쿼리를 Pinecone의 인덱스 쿼리로 변경합니다.
        # where={"user_id": user_id} 필터링 로직은 메타데이터 필터로 처리됩니다.
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=n_results,
            filter={"user_id": user_id}, # 메타데이터 필터링
            include_metadata=True
        )

        retrieved_docs = []
        for match in results.matches:
            # Pinecone 결과에서 문서 내용(metadata의 'text' 키 등)을 추출
            document_content = match.metadata.get('text', '문서 내용 없음')
            retrieved_docs.append(document_content)
            
        print(f"{len(retrieved_docs)}개의 관련 문서를 찾았습니다.")
        return retrieved_docs
    except Exception as e:
        print(f"문서 검색 중 오류가 발생했습니다: {e}")
        return []

# --- (parse_message_intent, generate_response 등 나머지 함수는 동일하게 유지) ---


if __name__ == "__main__":
    print("Ai 챗봇에 오신 것을 환영합니다! (Pinecone 버전)")
    print(f"'{PINECONE_INDEX_NAME}' 인덱스의 데이터를 기반으로 답변합니다.")
    print("종료하시려면 'exit' 또는 'quit'을 입력하세요.")

    # 🚨 중요: Pinecone을 사용하기 전, 벡터를 미리 인덱스에 '업서트(Upsert)'하는 과정이 필요합니다.
    # 이 예시에서는 생략했지만, 실제 운영 전에 별도의 스크립트로 데이터를 업로드해야 합니다.
    # 예: pinecone_index.upsert(vectors=[(id, vector, metadata)])
    
    # 예시 실행을 위해 user_id 임시 설정
    example_user_id = 1 

    while True:
        # 1. 사용자 질문 입력
        user_query = input("\n질문: ")

        if user_query.lower() in ["exit", "quit"]:
            print("챗봇을 종료합니다.")
            break

        if not user_query.strip():
            print("질문을 입력해주세요.")
            continue

        # 2. 관련 문서 검색
        # 'collection_name' 인자를 제거하고, user_id를 필터링 인자로 사용
        retrieved_documents = search_documents(
            user_query, user_id=example_user_id 
        )

@csrf_exempt # 개발 환경에서 테스트를 위해 CSRF를 임시로 비활성화합니다.
@require_POST
def send_message_api(request):
    try:
        data = json.loads(request.body)
        user_query = data.get('message', '').strip()
        user_id = 1 # 임시 사용자 ID
        
        if not user_query:
            return JsonResponse({'error': '메시지가 비어있습니다.'}, status=400)

        # 1. Pinecone 검색 실행
        retrieved_documents = search_documents(
            query=user_query, 
            user_id=user_id, 
            n_results=5 
        )

        final_response = generate_response(user_query, retrieved_documents)
        return JsonResponse({'response': final_response})
    
    except EnvironmentError as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        # 검색 또는 LLM 호출 중 발생한 예외 처리
        print(f"API 처리 중 오류 발생: {e}")
        return JsonResponse({'error': '서버 처리 중 오류가 발생했습니다.'}, status=500)        

def chat_view(request):
    return render(request, 'chat_app/chat_interface.html')


######################         일반 대화 응답           ###########################

FINETUNED_MODEL_ID = "gpt-3.5-turbo" # 사용할 LLM 모델 (gpt-4o가 더 좋지만 gpt-3.5-turbo도 충분합니다)

def generate_response(query: str, retrieved_docs: List[str]) -> str:
    """
    사용자 쿼리와 검색된 문서를 기반으로 LLM 응답을 생성합니다.
    """
    # 1. 시스템 프롬프트 생성 (RAG의 핵심)
    if retrieved_docs:
        # 검색된 문서가 있을 경우
        context = "\n\n".join(retrieved_docs)
        system_prompt = (
            "당신은 사용자의 개인 비서 챗봇입니다. "
            "사용자의 질문에 대해 아래에 제공된 '문서 내용'만을 사용하여 상세하고 친절하게 답변하세요. "
            "만약 문서 내용에 답변할 정보가 없다면, '정보를 찾을 수 없습니다'라고만 간단히 답변하세요."
            "\n\n--- 문서 내용 ---\n"
            f"{context}"
            "\n-------------------\n"
        )
    else:
        # 검색된 문서가 없을 경우 (일반 대화 모드)
        system_prompt = (
            "당신은 친절하고 도움이 되는 AI 챗봇입니다. "
            "현재는 검색할 문서가 없으므로 일반적인 지식과 상식에 기반하여 자연스러운 대화를 진행하세요."
        )

    # 2. OpenAI API 호출
    try:
        response = client_openai.chat.completions.create(
            model=FINETUNED_MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM 응답 생성 중 오류 발생: {e}")
        return "죄송합니다. AI 응답을 생성하는 중 서버 오류가 발생했습니다."
