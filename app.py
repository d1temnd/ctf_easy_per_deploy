from routes import app
from database import init_db
from docker_utils import auto_remove_containers
import threading

if __name__ == "__main__":
    init_db()  # Инициализируем базу данных
    threading.Thread(target=auto_remove_containers, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
