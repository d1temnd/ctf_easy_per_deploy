from routes import app
from database import init_db
from routes import *

if __name__ == "__main__":
    init_db()  # Инициализируем базу данных
    app.run(host="0.0.0.0", port=5000, debug=True)
