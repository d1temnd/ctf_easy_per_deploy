import flask 
from flask import make_response, render_template, request
import uuid
from ..database import execute_query
from ..config import add_time



main_page = flask.Blueprint('main_page')

@main_page.route("/")
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