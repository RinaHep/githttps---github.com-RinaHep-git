from flask import Flask
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Важно для работы сессий
bcrypt = Bcrypt(app)