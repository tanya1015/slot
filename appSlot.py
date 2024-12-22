from urllib.parse import uses_relative
from flask_migrate import Migrate
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import traceback
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///slot.db"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Таблица для новостей
class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # Название
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата
    content = db.Column(db.Text, nullable=False)  # Текст новости
    image_path = db.Column(db.String(200))  # Путь к картинке

    def __repr__(self):
        return f"<News {self.title}>"

# Таблица для мастеров
class Master(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)  # ФИО мастера
    age = db.Column(db.Integer, nullable=False)  # Возраст
    experience = db.Column(db.Integer, nullable=False)  # Стаж (в годах)
    description = db.Column(db.Text, nullable=True)  # Описание мастера

    def __repr__(self):
        return f"<Master {self.full_name}>"

# Таблица для расписания
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    master_id = db.Column(db.Integer, db.ForeignKey('master.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Свободно, Занято
    comment = db.Column(db.String(220))  # Поле для комментария

    master = db.relationship('Master', backref=db.backref('schedule', lazy=True))

    def __repr__(self):
        return f"<Schedule {self.date} - {self.master_id} ({self.status}): {self.comment}>"


# Таблица для услуг
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Название услуги

    def __repr__(self):
        return f"<Service {self.name}>"

# Таблица для цен
class Price(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)  # ID услуги
    price = db.Column(db.Float, nullable=False)  # Цена

    service = db.relationship('Service', backref=db.backref('prices', lazy=True))  # Связь с услугами

    def __repr__(self):
        return f"<Price {self.service.name} - {self.price}>"

# Таблица для рекомендаций
class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)  # Название рекомендации
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата
    content = db.Column(db.Text, nullable=False)  # Текст рекомендации

    def __repr__(self):
        return f"<Recommendation {self.title}>"

# Таблица для пользователей
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)  # Логин
    password = db.Column(db.String(120), nullable=False)  # Пароль

    def __repr__(self):
        return f"<User {self.username}>"

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120), nullable=False)
    master_id = db.Column(db.Integer, db.ForeignKey('master.id'), nullable=False)  # Мастер, о котором отзыв
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Дата отзыва
    content = db.Column(db.Text, nullable=False)  # Текст отзыва


@app.route('/', methods=['GET'])
def index():
    # Получаем список всех новостей из базы данных, сортируем по дате (новые сверху)
    news_list = News.query.order_by(News.date.desc()).all()
    return render_template("index.html", news_list=news_list)

@app.route('/masters')
def masters():
    # Получаем всех мастеров
    masters = Master.query.all()

    # Получаем расписания всех мастеров
    schedules = Schedule.query.all()

    # Передаем данные в шаблон
    return render_template('masters.html', masters=masters, schedules=schedules)

@app.route('/get_schedule')
def get_schedule():
    # Получаем дату из запроса
    date_str = request.args.get('date')

    if not date_str:
        return jsonify({"error": "Параметр date не передан в запросе"}), 400

    try:
        # Преобразуем строку в объект datetime
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Некорректный формат параметра date"}), 400

    # Получаем расписание из базы данных для указанной даты
    schedule_entries = Schedule.query.filter_by(date=date).all()

    # Формируем ответ с расписанием
    schedule_data = []
    for entry in schedule_entries:
        schedule_data.append({
            "master_name": entry.master.full_name,
            "master_description": entry.master.description,
            "status": entry.status,
            "comment": entry.comment
        })

    return jsonify(schedule_data), 200



@app.route('/reviews')
def reviews():
    # Получение всех отзывов из базы данных с привязкой к мастерам
    reviews = Review.query.join(Master, Review.master_id == Master.id).add_columns(
        Review.user, Master.full_name, Review.content, Review.date
    ).all()

    return render_template('reviews.html', reviews=reviews)


@app.route('/recommendations', methods=['GET'])
def recommendations():
    recommendations = Recommendation.query.all()  # Получаем все заметки из базы данных
    return render_template('recommendations.html', recommendations=recommendations)

@app.route('/price-list', methods=['GET'])
def price_list():
    # Получение всех записей из таблицы Price с соответствующими услугами
    prices = Price.query.join(Service).order_by(Service.name).all()
    return render_template('price-list.html', prices=prices)


@app.route('/admin_console', methods=['GET'])
def admin_console():
    return render_template('admin_console.html')

@app.route('/add_master', methods=['GET', 'POST'])
def add_master():
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            full_name = request.form['full_name']
            age = int(request.form['age'])
            experience = int(request.form['experience'])
            description = request.form['description']

            # Создаем запись мастера
            new_master = Master(
                full_name=full_name,
                age=age,
                experience=experience,
                description=description
            )
            db.session.add(new_master)
            db.session.commit()

            return redirect('/add_master')  # Перенаправляем на ту же страницу
        except Exception as e:
            # Ловим ошибки, если они есть
            return f"Ошибка при добавлении мастера: {str(e)}", 500

    # Если метод GET — рендерим шаблон
    return render_template('add_master.html')

@app.route('/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            master_id = request.form['master']
            status = request.form['status']
            comment = request.form.get('comment', '')  # Получаем комментарий, если есть

            # Создаем новую запись расписания
            new_schedule = Schedule(date=date, master_id=master_id, status=status, comment=comment)
            db.session.add(new_schedule)
            db.session.commit()

            return redirect('/add_schedule')  # Обновляем страницу после добавления
        except Exception as e:
            return f"Ошибка при добавлении расписания: {str(e)}"
    else:
        # Получаем список мастеров для отображения в форме
        masters = Master.query.all()
        return render_template('add_schedule.html', masters=masters)

@app.route('/add_service', methods=['GET', 'POST'])
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')  # Получаем название услуги из формы
        if not name:
            return redirect('/add_service')

        # Проверяем, есть ли услуга с таким названием
        existing_service = Service.query.filter_by(name=name).first()
        if existing_service:
            return redirect('/add_service')

        # Добавляем новую услугу в базу данных
        name = Service(name=name)
        db.session.add(name)
        db.session.commit()
        return redirect('/add_service')  # Перенаправление на панель администратора

    # GET запрос: возвращаем страницу с формой
    return render_template('add_service.html')

@app.route('/add_price', methods=['GET', 'POST'])
def add_price():
    if request.method == 'POST':
        service_id = request.form.get('service')  # Получаем ID услуги из формы
        price = request.form.get('price')  # Получаем цену из формы

        # Проверяем корректность данных
        if not service_id or not price:
            return redirect('/add_price')

        try:
            service_id = int(service_id)
            price = float(price)
        except ValueError:
            return redirect('/add_price')

        # Проверяем, существует ли такая услуга
        service = Service.query.get(service_id)
        if not service:
            return redirect('/add_price')

        # Проверяем, есть ли уже цена для этой услуги
        existing_price = Price.query.filter_by(service_id=service_id).first()
        if existing_price:
            return redirect('/add_price')

        # Добавляем новую цену в базу данных
        new_price = Price(service_id=service_id, price=price)
        db.session.add(new_price)
        db.session.commit()
        return redirect('/add_price')  # Перенаправление на панель администратора

    # GET запрос: загружаем список услуг для отображения в выпадающем списке
    services = Service.query.all()
    return render_template('add_price.html', services=services)

@app.route('/add_recommendation', methods=['GET', 'POST'])
def add_recommendation():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            return render_template('add_recommendation.html')

        # Добавление рекомендации в БД
        recommendation = Recommendation(title=title, content=content)
        db.session.add(recommendation)
        db.session.commit()

        return render_template('add_recommendation.html')

    # GET-запрос: отобразить шаблон
    return render_template('add_recommendation.html')

from werkzeug.security import generate_password_hash

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('add_user.html')

        # Проверка на уникальность имени пользователя
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('add_user.html')

        # Хэширование пароля перед сохранением
        hashed_password = generate_password_hash(password)

        # Добавление пользователя в БД
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()


        return render_template('add_user.html')

    # GET-запрос: отображение формы
    return render_template('add_user.html')

@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image = request.files.get('image')

        if not title or not content:
            return render_template('add_news.html')

        image_path = None
        if image and allowed_file(image.filename):
            # Сохранение изображения
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            # Приведение пути к универсальному формату
            image_path = image_path.replace("\\", "/")

        # Сохранение новости в базе данных
        news = News(title=title, content=content, image_path=image_path)
        db.session.add(news)
        db.session.commit()

        return render_template('add_news.html')

    # GET-запрос: отображение формы
    return render_template('add_news.html')

@app.route('/add_review', methods=['GET','POST'])
def add_review():
    if request.method == 'POST':
        # Получение данных из формы
        user = request.form.get('user')  # ФИО пользователя
        master_id = request.form.get('master_id')  # ID мастера
        content = request.form.get('content')  # Текст отзыва

        # Проверка на заполненность полей
        if not all([user, master_id, content]):
            return redirect(request.referrer)

        # Создание нового отзыва
        review = Review(
            user=user,
            master_id=master_id,
            content=content
        )

        # Сохранение отзыва в базе данных
        db.session.add(review)
        db.session.commit()

        return redirect('/reviews')  # Переход на страницу со списком отзывов
        # GET-запрос: отображение формы
        # Получаем всех мастеров из базы
    masters = Master.query.all()
    return render_template('add_review.html', masters=masters)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)