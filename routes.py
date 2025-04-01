from flask import Flask, jsonify, render_template, request, make_response
import threading
import time
import uuid
import docker
from datetime import datetime, timedelta
from database import execute_query, remove_container_from_db
from docker_utils import get_free_port, client, auto_remove_container, remove_container
from config import IMAGES_NAME, LEAVE_TIME, ADD_TIME, FLAG, PORT_IN_CONTAINER

app = Flask(__name__)

@app.template_filter('to_datetime')
def to_datetime_filter(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

@app.route("/")
def index():
    user_uuid = request.cookies.get('user_uuid')

    if not user_uuid:
        user_uuid = str(uuid.uuid4())
        response = make_response(render_template("index.html", user_container=None, add_minutes=(ADD_TIME // 60)))
        response.set_cookie('user_uuid', user_uuid)
        return response

    user_container = execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    response = make_response(render_template("index.html", user_container=user_container, add_minutes=(ADD_TIME // 60)))
    return response

@app.route("/deploy", methods=["POST"])
def deploy_container():
    user_uuid = request.cookies.get('user_uuid')

    existing_container = execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    if existing_container:
        return jsonify({"error": "You already have a running container"}), 400

    port = get_free_port()
    if not port:
        return jsonify({"error": "No available ports"}), 400

    expiration_time = int(time.time()) + LEAVE_TIME

    # Создаем запись в базе данных без ID контейнера
    execute_query(
        "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid) VALUES (?, ?, ?, ?, ?)",
        (None, port, int(time.time()), expiration_time, user_uuid)
    )

    # Проверяем, существует ли локальный образ
    try:
        client.images.get(IMAGES_NAME)
    except docker.errors.ImageNotFound:
        build_log = client.images.build(path="./deploy_task", tag=IMAGES_NAME)
        print("Image built:", build_log)

    # Запускаем контейнер
    container = client.containers.run(IMAGES_NAME, detach=True, ports={PORT_IN_CONTAINER: port}, environment={'FLAG': FLAG})

    # Обновляем ID контейнера в БД
    execute_query(
        "UPDATE containers SET id = ? WHERE port = ?",
        (container.id, port)
    )

    threading.Thread(target=auto_remove_container, args=(container.id, port)).start()

    return jsonify({"message": "Container started", "port": port, "id": container.id, "expiration_time": expiration_time})

@app.route("/stop", methods=["POST"])
def stop_container():
    user_uuid = request.cookies.get('user_uuid')

    container_data = execute_query("SELECT id, port FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    if not container_data:
        return jsonify({"error": "No active container"}), 400

    container_id, port = container_data

    remove_container(container_id, port)

    return jsonify({"message": "Container stopped"})


@app.route("/restart", methods=["POST"])
def restart_container():
    user_uuid = request.cookies.get('user_uuid')  # Чтение UUID из куки

    container_data = execute_query("SELECT id FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    if not container_data:
        return jsonify({"error": "No active container"}), 400
    container_id = container_data[0]
    
    try:
        container = client.containers.get(container_id)
        container.restart()
    except docker.errors.NotFound:
        return jsonify({"error": "Container not found"}), 404
    
    return jsonify({"message": "Container restarted"})


@app.route("/extend", methods=["POST"])
def extend_container_lifetime():
    user_uuid = request.cookies.get('user_uuid')

    container_data = execute_query("SELECT id, expiration_time FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    if not container_data:
        return jsonify({"error": "No active container"}), 400
        
    container_id, expiration_time = container_data
    
    # Увеличиваем время жизни контейнера на add_time
    new_expiration_time = expiration_time + ADD_TIME  # добавляем время в секундах
    
    # Обновляем время жизни в базе данных
    execute_query(
        "UPDATE containers SET expiration_time = ? WHERE id = ?", 
        (new_expiration_time, container_id)
    )

    return jsonify({"message": "Container lifetime extended", "new_expiration_time": new_expiration_time})