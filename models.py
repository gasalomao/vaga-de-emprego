# models.py

from extensions import db
from datetime import datetime

# Modelo do Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship("Task", back_populates="user", lazy=True)
    messages = db.relationship("Message", back_populates="user", lazy=True)

# Modelo de Mensagem de Chat
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' ou 'assistant'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="messages")

# Modelo do Banco de Dados
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False)
    cost = db.Column(db.Float, nullable=False, default=0.0)
    due_date = db.Column(db.Date, nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    priority = db.Column(db.String(50), nullable=True)
    assigned_to = db.Column(db.String(100), nullable=True)
    created_by = db.Column(db.String(100), nullable=True)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completion_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)

    # Relacionamento com o usuário
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="tasks")

    @property
    def duration(self):
        """Calcula o tempo desde o registro até o momento atual."""
        time_since = datetime.utcnow() - self.creation_date
        days = time_since.days
        hours, remainder = divmod(time_since.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if days > 0:
            return f"{days} dias, {hours} horas e {minutes} minutos"
        else:
            return f"{hours} horas e {minutes} minutos"
