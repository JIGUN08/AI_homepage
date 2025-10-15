from django.db import models
from django.contrib.auth.models import User

# NOTE: 기존 ChatMessage, UserAttribute, UserProfile 등 모델들은 
# 이 파일에 이미 정의되어 있다고 가정합니다.

# ----------------------------------------------------
# 🌟 신규: 게임/인테리어 기능 관련 모델 🌟
# ----------------------------------------------------

class Room(models.Model):
    """
    사용자 한 명당 하나의 가상 방 환경을 정의합니다.
    (예: 방 크기, 배경 스타일 등)
    """
    # User 모델과 1:1 관계 (사용자 한 명당 방 하나)
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True) 
    room_name = models.CharField(max_length=100, default="나만의 아늑한 방")
    background_style = models.CharField(max_length=50, default="modern_white") # Flutter에서 사용할 배경 이미지/색상 키
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Room ({self.room_name})"

class FurnitureItem(models.Model):
    """
    사용자 방에 배치된 개별 가구 아이템의 위치와 상태를 저장합니다.
    """
    # Room 모델과 다수:1 관계 (하나의 방에 여러 가구 아이템)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='furniture_items')
    item_type = models.CharField(max_length=50) # 가구의 종류 (예: 'bed', 'desk', 'sofa')
    
    # 2D 또는 3D 환경을 위한 위치 좌표
    position_x = models.FloatField(default=0.0)
    position_y = models.FloatField(default=0.0)
    position_z = models.FloatField(default=0.0) 
    
    rotation = models.FloatField(default=0.0) # 회전 각도 (Flutter 렌더링에 사용)
    scale = models.FloatField(default=1.0) # 크기 배율
    
    custom_name = models.CharField(max_length=100, blank=True, null=True) # 사용자가 지정한 가구 이름
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 최근에 생성된 아이템을 나중에 정렬하기 쉽게 합니다.
        ordering = ['created_at'] 

    def __str__(self):
        return f"{self.item_type} in {self.room.user.username}'s room at ({self.position_x}, {self.position_y})"
