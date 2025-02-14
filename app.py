from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
)
from functools import wraps
import os
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

app = Flask(
    __name__, template_folder="src/templates", static_folder="src/static"
)

MOVIES_API_URL = "https://bookapi.impaas.uk/movies"

# Configuration
app.config["SECRET_KEY"] = os.urandom(24)

# Initialize Supabase client
supabase: Client = create_client(
    "https://euibanwordbygkxadvrx.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV1aWJhbndvcmRieWdreGFkdnJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkzNjM2NDcsImV4cCI6MjA1NDkzOTY0N30.E5AeoS2-6vCHnt1PqsGAtMnaBB8xR48D8XhJ4jvwoEk",
)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    success = request.args.get("success")
    if request.method == "POST":
        try:
            username = request.form["username"]
            password = request.form["password"]

            # Get user from database
            user_response = supabase.table("profiles").select("*").eq("username", username).execute()

            if not user_response.data:
                return render_template("login.html", error="Invalid credentials")

            user_data = user_response.data[0]

            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
                # Store user info in session
                session["user_id"] = user_data["id"]
                session["username"] = user_data["username"]
                session["is_admin"] = user_data["is_admin"]

                if user_data["is_admin"]:
                    return redirect(url_for("admin"))
                return redirect(url_for("search"))
            else:
                return render_template("login.html", error="Invalid credentials")

        except Exception as e:
            print(f"Login error: {e}")
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html", success=success)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username = request.form["username"]
            password = request.form["password"]

            if not username or not password:
                return render_template(
                    "register.html", error="Username and password are required"
                )

            # Check if username already exists
            existing_user = (
                supabase.table("profiles")
                .select("username")
                .eq("username", username)
                .execute()
            )
            if existing_user.data:
                return render_template(
                    "register.html", error="Username already exists"
                )

            # Hash the password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

            # Create profile entry
            profile_data = {
                "username": username,
                "password": hashed_password.decode('utf-8'),
                "is_admin": False,
            }

            supabase.table("profiles").insert(profile_data).execute()

            return redirect(
                url_for(
                    "login",
                    success="Registration successful. Please login now.",
                )
            )

        except Exception as e:
            print(f"Registration error: {e}")
            error_message = str(e)
            return render_template("register.html", error=error_message)

    return render_template("register.html")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    try:
        response = requests.get(f"{MOVIES_API_URL}?page=1&per_page=1000")
        response.raise_for_status()
        movies_data = response.json().get("movies", [])
    except requests.RequestException as e:
        print(f"Error fetching movies: {e}")
        return render_template(
            "search.html", username=session.get("username"), movies=[]
        )

    if request.method == "POST":
        search_data = request.form
    else:
        search_data = request.args

    filtered_movies = movies_data

    return render_template(
        "search.html", username=session.get("username"), movies=filtered_movies
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    try:
        response = supabase.table("profiles").select("*").execute()
        users = response.data
        return render_template(
            "admin.html", username=session.get("username"), users=users
        )
    except Exception as e:
        print(f"Admin page error: {e}")
        return "Error loading admin page", 500


@app.route("/api/users")
@admin_required
def get_users():
    try:
        response = supabase.table("profiles").select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    try:
        new_password = request.json.get("newPassword")
        if not new_password:
            return jsonify({"error": "New password is required"}), 400

        # Hash the new password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)

        # Update user's password in Supabase
        supabase.table("profiles").update(
            {"password": hashed_password.decode('utf-8')}
        ).eq("id", user_id).execute()

        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>/username", methods=["PUT"])
@admin_required
def update_username(user_id):
    try:
        new_username = request.json.get("newUsername")
        if not new_username:
            return jsonify({"error": "New username is required"}), 400

        # Update username in profiles table
        supabase.table("profiles").update({"username": new_username}).eq(
            "id", user_id
        ).execute()

        return jsonify({"message": "Username updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    try:
        # Delete user from profiles
        supabase.table("profiles").delete().eq("id", user_id).execute()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)