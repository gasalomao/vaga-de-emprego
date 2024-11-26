# forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    FloatField,
    SubmitField,
    TextAreaField,
    SelectField,
    PasswordField,
)
from wtforms.validators import DataRequired, ValidationError, EqualTo, Optional
from models import User, Task
from flask import session
from datetime import datetime

class RegistrationForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired()])
    password = PasswordField(
        "Senha",
        validators=[
            DataRequired(),
            EqualTo("confirm", message="As senhas devem coincidir."),
        ],
    )
    confirm = PasswordField("Confirme a Senha", validators=[DataRequired()])
    submit = SubmitField("Registrar")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Nome de usuário já existe.")

class LoginForm(FlaskForm):
    username = StringField("Usuário", validators=[DataRequired()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")

class TaskForm(FlaskForm):
    task_name = StringField("Nome da Tarefa", validators=[DataRequired()])
    cost = FloatField("Custo (R$)", validators=[DataRequired()])
    due_date = StringField(
        "Data Limite",
        validators=[DataRequired()],
        render_kw={"placeholder": "dd/mm/yyyy"}
    )
    description = TextAreaField("Descrição", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[
            ("Pendente", "Pendente"),
            ("Em Andamento", "Em Andamento"),
            ("Concluída", "Concluída"),
        ],
        validators=[Optional()],
    )
    priority = SelectField(
        "Prioridade",
        choices=[
            ("Baixa", "Baixa"),
            ("Média", "Média"),
            ("Alta", "Alta"),
        ],
        validators=[Optional()],
    )
    assigned_to = StringField("Atribuída a", validators=[Optional()])
    created_by = StringField("Criada por", validators=[Optional()])
    completion_date = StringField(
        "Data de Conclusão",
        validators=[Optional()],
        render_kw={"placeholder": "dd/mm/yyyy"}
    )
    notes = TextAreaField("Notas", validators=[Optional()])
    category = StringField("Categoria", validators=[Optional()])
    submit = SubmitField("Salvar")

    def validate_task_name(self, task_name):
        if task_name.data:
            task = Task.query.filter_by(task_name=task_name.data, user_id=session.get("user_id")).first()
            if task and (not hasattr(self, "original_task_name") or task_name.data != self.original_task_name):
                raise ValidationError("Nome da tarefa já existe.")

    def validate_due_date(self, due_date):
        if due_date.data:
            try:
                datetime.strptime(due_date.data, "%d/%m/%Y")
            except ValueError:
                raise ValidationError("Formato de data inválido. Use dd/mm/yyyy.")

    def validate_completion_date(self, completion_date):
        if completion_date.data:
            try:
                datetime.strptime(completion_date.data, "%d/%m/%Y")
            except ValueError:
                raise ValidationError("Formato de data inválido. Use dd/mm/yyyy.")
