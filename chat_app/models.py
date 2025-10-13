# chat_app/models.py

from django.db import models

class UserProfile(models.Model):
    # Django 기본 User 모델을 확장하거나, 별도의 사용자 ID/프로필 관리
    user_id = models.IntegerField(unique=True) 
    username = models.CharField(max_length=100)
    affinity_score = models.IntegerField(default=50) # 페르소나 호감도 점수 (0-100)
    
    # RAG에 사용할 사용자 정보 (위치 정보, 관계 정보 등)
    location_info = models.TextField(default="")
    relationship_info = models.TextField(default="") 
    
    def __str__(self):
        return self.username

class ChatHistory(models.Model):
    # 사용자와 AI의 대화 기록
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message_role = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')]) # 'user' 또는 'ai'
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user_profile.username} - {self.message_role} at {self.timestamp}"
