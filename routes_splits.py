from flask import Flask, jsonify, render_template, request, make_response
import threading
import time
import uuid
import docker
from database import execute_query, remove_container_from_db
from docker_utils import get_free_port, client, auto_remove_container
from config import images_name, leave_time, add_time

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
        response = make_response(render_template("index.html", user_container=None, add_minutes=(add_time // 60)))
        response.set_cookie('user_uuid', user_uuid)
        return response

    user_container = execute_query("SELECT * FROM containers WHERE user_uuid = ?", (user_uuid,), fetchone=True)
    response = make_response(render_template("index.html", user_container=user_container, add_minutes=(add_time // 60)))
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

    expiration_time = int(time.time()) + leave_time
    
    container = client.containers.run(images_name, detach=True, ports={"80/tcp": port})

    execute_query(
        "INSERT INTO containers (id, port, start_time, expiration_time, user_uuid) VALUES (?, ?, ?, ?, ?)",
        (container.id, port, int(time.time()), expiration_time, user_uuid)
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

    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass

    remove_container_from_db(container_id)

    return jsonify({"message": "Container stopped"})
