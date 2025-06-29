from functools import wraps
from flask import redirect, session, url_for

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
