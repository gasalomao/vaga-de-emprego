# api/app.py

from flask import Flask, render_template, redirect, url_for, flash, request, session
from extensions import db
from forms import RegistrationForm, LoginForm, TaskForm
from models import User, Task, Message
import os
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Carregar variáveis de ambiente do .env
load_dotenv()

# Configurar a API Gemini
genai.configure(api_key=os.getenv("API_KEY"))

app = Flask(__name__)

# Definir a chave secreta
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "chave_secreta_padrao_para_desenvolvimento"

# Configuração do banco de dados
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL") or "sqlite:///tasks.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar o banco de dados
db.init_app(app)

# Função para injetar o ano atual no contexto do template
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

# Decorador para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" in session:
            return f(*args, **kwargs)
        else:
            flash("Por favor, faça login primeiro.", "warning")
            return redirect(url_for("login"))
    return wrap

# Rotas de Autenticação
@app.route("/register", methods=["GET", "POST"])
def register():
    # Se o usuário já estiver logado, redireciona para a lista de tarefas
    if "user_id" in session:
        return redirect(url_for("index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    # Se o usuário já estiver logado, redireciona para a lista de tarefas
    if "user_id" in session:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("index"))
        else:
            flash("Credenciais inválidas.", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("login"))

# Rotas Principais
@app.route("/")
@login_required
def index():
    tasks = Task.query.filter_by(user_id=session["user_id"]).order_by(Task.display_order).all()
    return render_template("tasks.html", tasks=tasks)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        # Verificar se o nome da tarefa já existe para este usuário
        existing_task = Task.query.filter_by(task_name=form.task_name.data, user_id=session["user_id"]).first()
        if existing_task:
            form.task_name.errors.append("Nome da tarefa já existe.")
            return render_template("add_task.html", form=form)

        # Determinar o display_order
        max_order = db.session.query(db.func.max(Task.display_order)).filter_by(user_id=session["user_id"]).scalar()
        display_order = (max_order + 1) if max_order else 1

        # Converter strings de data para objetos date
        try:
            due_date = datetime.strptime(form.due_date.data, "%d/%m/%Y").date()
        except ValueError:
            form.due_date.errors.append("Formato de data inválido. Use dd/mm/yyyy.")
            return render_template("add_task.html", form=form)

        if form.completion_date.data:
            try:
                completion_date = datetime.strptime(form.completion_date.data, "%d/%m/%Y").date()
            except ValueError:
                form.completion_date.errors.append("Formato de data inválido. Use dd/mm/yyyy.")
                return render_template("add_task.html", form=form)
        else:
            completion_date = None

        new_task = Task(
            task_name=form.task_name.data,
            cost=form.cost.data,
            due_date=due_date,
            description=form.description.data,
            status=form.status.data if form.status.data else None,
            priority=form.priority.data if form.priority.data else None,
            assigned_to=form.assigned_to.data,
            created_by=form.created_by.data,
            creation_date=datetime.utcnow(),
            completion_date=completion_date,
            notes=form.notes.data,
            category=form.category.data,
            display_order=display_order,
            user_id=session["user_id"],
        )
        db.session.add(new_task)
        db.session.commit()
        flash("Tarefa adicionada com sucesso!", "success")
        return redirect(url_for("index"))
    return render_template("add_task.html", form=form)

@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    form = TaskForm(obj=task)
    form.original_task_name = task.task_name
    if request.method == "GET":
        # Pre-popular os campos de data no formato correto
        form.due_date.data = task.due_date.strftime("%d/%m/%Y")
        if task.completion_date:
            form.completion_date.data = task.completion_date.strftime("%d/%m/%Y")
    if form.validate_on_submit():
        if form.task_name.data != task.task_name:
            # Verificar se o novo nome já existe
            existing_task = Task.query.filter_by(task_name=form.task_name.data, user_id=session["user_id"]).first()
            if existing_task:
                form.task_name.errors.append("Nome da tarefa já existe.")
                return render_template("edit_task.html", form=form, task=task)
        task.task_name = form.task_name.data
        task.cost = form.cost.data
        # Converter strings de data para objetos date
        try:
            task.due_date = datetime.strptime(form.due_date.data, "%d/%m/%Y").date()
        except ValueError:
            form.due_date.errors.append("Formato de data inválido. Use dd/mm/yyyy.")
            return render_template("edit_task.html", form=form, task=task)

        if form.completion_date.data:
            try:
                task.completion_date = datetime.strptime(form.completion_date.data, "%d/%m/%Y").date()
            except ValueError:
                form.completion_date.errors.append("Formato de data inválido. Use dd/mm/yyyy.")
                return render_template("edit_task.html", form=form, task=task)
        else:
            task.completion_date = None

        task.description = form.description.data
        task.status = form.status.data if form.status.data else None
        task.priority = form.priority.data if form.priority.data else None
        task.assigned_to = form.assigned_to.data
        task.created_by = form.created_by.data
        task.notes = form.notes.data
        task.category = form.category.data
        db.session.commit()
        flash("Tarefa atualizada com sucesso!", "success")
        return redirect(url_for("index"))
    return render_template("edit_task.html", form=form, task=task)

@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(task)
    db.session.commit()
    # Reordenar display_order
    tasks = Task.query.filter_by(user_id=session["user_id"]).order_by(Task.display_order).all()
    for index, task in enumerate(tasks):
        task.display_order = index + 1
    db.session.commit()
    flash("Tarefa excluída com sucesso!", "success")
    return redirect(url_for("index"))

@app.route("/move_up/<int:task_id>", methods=["POST"])
@login_required
def move_up(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    if task.display_order == 1:
        flash("Esta tarefa já está no topo.", "warning")
    else:
        above_task = Task.query.filter_by(display_order=task.display_order - 1, user_id=session["user_id"]).first()
        if above_task:
            # Trocar os display_order
            task.display_order, above_task.display_order = above_task.display_order, task.display_order
            db.session.commit()
            flash("Tarefa movida para cima com sucesso!", "success")
    return redirect(url_for("index"))

@app.route("/move_down/<int:task_id>", methods=["POST"])
@login_required
def move_down(task_id):
    task = Task.query.filter_by(id=task_id, user_id=session["user_id"]).first_or_404()
    max_order = db.session.query(db.func.max(Task.display_order)).filter_by(user_id=session["user_id"]).scalar()
    if task.display_order == max_order:
        flash("Esta tarefa já está na última posição.", "warning")
    else:
        below_task = Task.query.filter_by(display_order=task.display_order + 1, user_id=session["user_id"]).first()
        if below_task:
            # Trocar os display_order
            task.display_order, below_task.display_order = below_task.display_order, task.display_order
            db.session.commit()
            flash("Tarefa movida para baixo com sucesso!", "success")
    return redirect(url_for("index"))

@app.route("/generate_report", methods=["GET", "POST"])
@login_required
def generate_report():
    if request.method == "POST":
        selected_task_ids = request.form.getlist("task_ids")
        if not selected_task_ids:
            flash("Por favor, selecione pelo menos uma tarefa.", "warning")
            return redirect(url_for("generate_report"))
        tasks = Task.query.filter(Task.id.in_(selected_task_ids), Task.user_id == session["user_id"]).order_by(Task.display_order).all()

        # Preparar o prompt para a IA com instruções claras para evitar invenções
        prompt = (
            "Você é um assistente responsável por gerar relatórios precisos e objetivos com base nos dados fornecidos. "
            "Utilize **apenas** as informações abaixo para criar o relatório. Não adicione informações ou detalhes que não estejam presentes nos dados.\n\n"
            "### Relatório de Tarefas\n\n"
        )
        for idx, task in enumerate(tasks, start=1):
            prompt += f"**Tarefa {idx}:**\n"
            prompt += f"- **Nome da Tarefa:** {task.task_name}\n"
            prompt += f"- **Custo:** R${task.cost:.2f}\n"
            prompt += f"- **Data Prevista para Inicialização:** {task.due_date.strftime('%d/%m/%Y')}\n"
            prompt += f"- **Descrição:** {task.description if task.description else 'N/A'}\n"
            prompt += f"- **Status:** {task.status if task.status else 'N/A'}\n"
            prompt += f"- **Prioridade:** {task.priority if task.priority else 'N/A'}\n"
            prompt += f"- **Atribuída a:** {task.assigned_to if task.assigned_to else 'N/A'}\n"
            prompt += f"- **Criada por:** {task.created_by if task.created_by else 'N/A'}\n"
            prompt += f"- **Data de Conclusão:** {task.completion_date.strftime('%d/%m/%Y') if task.completion_date else 'N/A'}\n"
            prompt += f"- **Notas:** {task.notes if task.notes else 'N/A'}\n"
            prompt += f"- **Categoria:** {task.category if task.category else 'N/A'}\n\n"

        prompt += (
            "Com base nas informações acima, gere um relatório detalhado. Mantenha o relatório objetivo, "
            "evitando adicionar opiniões ou informações que não estejam presentes nos dados fornecidos. "
            "Estruture o relatório com cabeçalhos claros para cada tarefa e inclua uma visão geral no início."
        )

        # Chamar a API Gemini
        try:
            # Inicializar o modelo Gemini
            model = genai.GenerativeModel("gemini-1.5-flash")
            # Gerar o conteúdo passando o prompt como argumento posicional
            response = model.generate_content(prompt)
            report = response.text
            return render_template("report.html", report=report)
        except Exception as e:
            app.logger.error(f"Erro ao gerar o relatório: {e}")
            flash("Erro ao gerar o relatório. Verifique sua chave de API e tente novamente.", "danger")
            return redirect(url_for("generate_report"))
    else:
        tasks = Task.query.filter_by(user_id=session["user_id"]).order_by(Task.display_order).all()
        return render_template("generate_report.html", tasks=tasks)

# Rota para o Chatbot
@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        user_message = request.form.get("message")
        if user_message:
            # Salvar a mensagem do usuário
            message = Message(user_id=session["user_id"], content=user_message, role="user")
            db.session.add(message)
            db.session.commit()

            # Chamar a API Gemini para gerar a resposta
            try:
                # Inicializar o modelo Gemini
                model = genai.GenerativeModel("gemini-1.5-flash")
                # Gerar a resposta passando a mensagem do usuário
                response = model.generate_content(user_message)
                ai_response = response.text

                # Salvar a resposta da IA
                ai_message = Message(user_id=session["user_id"], content=ai_response, role="assistant")
                db.session.add(ai_message)
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Erro ao gerar a resposta: {e}")
                flash("Erro ao gerar a resposta. Verifique sua chave de API e tente novamente.", "danger")
                ai_response = "Desculpe, ocorreu um erro ao processar sua solicitação."
                ai_message = Message(user_id=session["user_id"], content=ai_response, role="assistant")
                db.session.add(ai_message)
                db.session.commit()

        return redirect(url_for("chat"))
    else:
        messages = Message.query.filter_by(user_id=session["user_id"]).order_by(Message.timestamp).all()
        return render_template("chat.html", messages=messages)

@app.route("/delete_message/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    message = Message.query.filter_by(id=message_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(message)
    db.session.commit()
    flash("Mensagem excluída com sucesso!", "success")
    return redirect(url_for("chat"))

# Criação das tabelas no banco de dados
with app.app_context():
    db.create_all()

# Função de entrada para o Vercel
def handler(request, start_response):
    return app.wsgi_app(request.environ, start_response)
