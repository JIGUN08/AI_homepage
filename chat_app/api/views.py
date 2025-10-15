import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import ChatMessage # ChatMessage 모델 임포트 가정
from ..services.chat_service import process_chat_interaction
from .serializers import ChatPairSerializer 

# ----------------------------------------------------
# 1. 채팅 기록 로드 API (GET)
# Endpoint: /api/chat/history/
# ----------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated]) # 👈 인증된 사용자만 접근 가능 (Flutter에서 토큰 필요)
def get_chat_history(request):
    """
    사용자 채팅 기록을 로드하고, 사용자-AI 메시지 쌍으로 묶어 JSON 목록으로 반환합니다.
    """
    user = request.user
    
    # 1. AI 응답 메시지만 가져오고 최신 순으로 정렬합니다. (Flutter의 reverse: true에 맞춤)
    ai_messages = ChatMessage.objects.filter(user=user, is_user=False).order_by('-timestamp')
    
    chat_pairs = []
    
    for ai_msg in ai_messages:
        # 2. 각 AI 메시지보다 timestamp가 '같거나' 이전인 가장 최신 사용자 메시지를 찾습니다.
        user_msg = ChatMessage.objects.filter(
            user=user, 
            is_user=True, 
            timestamp__lte=ai_msg.timestamp 
        ).order_by('-timestamp').first()

        if user_msg:
            # 3. Flutter ChatPairSerializer에 맞게 딕셔너리 쌍 생성
            chat_pair = {
                'id': ai_msg.id,          # AI 메시지 ID를 쌍의 고유 ID로 사용
                'user_msg': user_msg.message,
                'ai_msg': ai_msg.message, # AI 응답 텍스트
                'timestamp': ai_msg.timestamp,
            }
            chat_pairs.append(chat_pair)
        else:
            print(f"[History Error] AI 메시지(ID: {ai_msg.id})에 대응하는 사용자 메시지를 찾을 수 없습니다.")

    # 4. Serializer를 사용하여 List[Dict]를 JSON으로 변환
    serializer = ChatPairSerializer(chat_pairs, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)

# ----------------------------------------------------
# 2. 채팅 메시지 전송 API (POST)
# Endpoint: /api/chat/send/
# ----------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_chat_message(request):
    """
    Flutter 앱으로부터 받은 메시지를 AI 로직에 전달하고, 결과 응답 메시지 쌍을 JSON으로 반환합니다.
    """
    try:
        # 1. 메시지 텍스트 추출
        data = json.loads(request.body)
        user_message_text = data.get('message')
        
        if not user_message_text:
            return Response(
                {"error": "메시지 내용이 필요합니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 기존 AI 로직 서비스 호출 (가장 중요한 단계: Pinecone, LLM, RDB 저장 모두 여기서 처리됨)
        result = process_chat_interaction(request, user_message_text)
        
        bot_message_id = result.get('bot_message_id')
        bot_message_text = result.get('bot_message')
        
        if not bot_message_id:
            return Response(
                {"error": "AI 응답 생성에 실패했습니다.", "detail": bot_message_text},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 3. 새로 생성된 AI 응답 객체를 RDB에서 가져옵니다.
        ai_msg_obj = ChatMessage.objects.get(id=bot_message_id)

        # 4. 새로 생성된 AI 메시지의 직전 사용자 메시지를 찾아 쌍을 이룹니다.
        user_msg_obj = ChatMessage.objects.filter(
            user=request.user, 
            is_user=True, 
            timestamp__lte=ai_msg_obj.timestamp
        ).order_by('-timestamp').first()

        # 5. Flutter Serializer에 맞게 데이터 준비 및 변환
        chat_pair = {
            'id': ai_msg_obj.id,
            'user_msg': user_msg_obj.message if user_msg_obj else user_message_text,
            'ai_msg': bot_message_text,
            'timestamp': ai_msg_obj.timestamp,
        }

        serializer = ChatPairSerializer(chat_pair)
        
        # 6. 성공 JSON 응답 반환
        return Response(serializer.data, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return Response(
            {"error": "잘못된 JSON 형식입니다."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"[Send Error] 메시지 전송 처리 중 오류 발생: {e}")
        return Response(
            {"error": "서버 처리 중 알 수 없는 오류가 발생했습니다."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


from rest_framework import serializers
from ..models import Room, FurnitureItem # Room, FurnitureItem 모델 임포트

# ----------------------------------------------------
# 기존 채팅 Serializer
# ----------------------------------------------------
class ChatPairSerializer(serializers.Serializer):
    """
    Flutter의 ChatMessageModel (사용자 메시지와 AI 응답 한 쌍) 형식에 맞춰
    데이터를 직렬화하기 위한 커스텀 Serializer입니다.
    
    이 Serializer는 뷰에서 직접 가공한 딕셔너리(메시지 쌍)를 받습니다.
    """
    # Flutter model: id (AI message ID), userMessage, aiResponse, timestamp (AI message timestamp)
    
    id = serializers.IntegerField(help_text="AI 응답 메시지의 고유 ID")
    user_message = serializers.CharField(source='user_msg', help_text="사용자가 보낸 메시지 텍스트")
    ai_response = serializers.CharField(source='ai_msg', help_text="AI가 응답한 메시지 텍스트")
    timestamp = serializers.DateTimeField(help_text="AI 응답이 생성된 시간")
    
    # Python의 snake_case(user_msg)를 Flutter의 camelCase(userMessage)로 변환하고
    # DateTime 객체를 ISO 8601 형식의 문자열로 변환합니다.
    def to_representation(self, instance):
        return {
            'id': instance['id'],
            'user_message': instance['user_msg'],
            'ai_response': instance['ai_msg'],
            'timestamp': instance['timestamp'].isoformat(),
        }

# ----------------------------------------------------
# 🌟 신규: 가구 인테리어 Serializers 🌟
# ----------------------------------------------------
class FurnitureItemSerializer(serializers.ModelSerializer):
    """
    FurnitureItem 모델을 Flutter용 JSON으로 변환합니다.
    """
    class Meta:
        model = FurnitureItem
        # id는 자동으로 포함되며, room 필드는 RoomSerializer에서 처리합니다.
        fields = (
            'id', 'item_type', 'position_x', 'position_y', 'position_z', 
            'rotation', 'scale', 'custom_name'
        )
        read_only_fields = ('id',) # id는 생성 시 자동으로 부여

class RoomSerializer(serializers.ModelSerializer):
    """
    Room 모델과 이에 속한 모든 FurnitureItem을 함께 직렬화합니다.
    """
    # related_name='furniture_items'를 사용하여 가구 목록을 Nested Serializer로 포함
    furniture_items = FurnitureItemSerializer(many=True, read_only=True) 

    class Meta:
        model = Room
        # user는 primary_key이고 요청 시점에서 결정되므로 fields에서 제외합니다.
        fields = ('room_name', 'background_style', 'furniture_items', 'last_updated')
        read_only_fields = ('furniture_items', 'last_updated') 

