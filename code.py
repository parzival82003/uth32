import requests
from flask import Flask, render_template, request
import sqlite3
import random
import string
import redis
from validators import url as validate_url
from flask_wtf.csrf import CSRFProtect
from passlib.hash import bcrypt

app = Flask(__name__)
app.debug = True  # Enable debug mode for detailed error messages

# Connect to Redis
redis_host = 'localhost'
redis_port = 6379
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Enable CSRF protection
csrf = CSRFProtect(app)

# Initialize database connection
db = sqlite3.connect('website_health.db')
cursor = db.cursor()

# Create table if not exists
cursor.execute("CREATE TABLE IF NOT EXISTS website_health (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, status TEXT)")

def generate_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))

def insert_random_data():
    for _ in range(10):
        url = f"https://{generate_random_string(10)}.com"
        status = random.choice(["Healthy"])
        cursor.execute("INSERT INTO website_health (url, status) VALUES (?, ?)", (url, status))

    db.commit()

def check_health(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return "Healthy"
        else:
            return "Unhealthy"
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking health: {str(e)}")
        return "Unhealthy"

def perform_security_test(url):
    if url.startswith("http://"):
        return "Insecure"
    else:
        return "Secure"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
@csrf.exempt  # Exclude CSRF protection for this route
def check():
    website_url = request.form['website_url']
    
    if not validate_url(website_url):
        return render_template('error.html', message='Invalid URL')

    health_status = check_health(website_url)
    security_status = perform_security_test(website_url)

    try:
        cursor.execute("INSERT INTO website_health (url, status) VALUES (?, ?)", (website_url, health_status))
        db.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while inserting data into the database: {str(e)}")

    try:
        redis_client.set(website_url, health_status)
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {str(e)}")
    
    redis_output = redis_client.get(website_url).decode('utf-8')
    
    return render_template('result.html', website_url=website_url, health_status=health_status, redis_output=redis_output, security_test=security_status)

if __name__ == '__main__':
    try:
        insert_random_data()
        app.run()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
