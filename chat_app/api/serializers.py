from rest_framework import serializers

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
