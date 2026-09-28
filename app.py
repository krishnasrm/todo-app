from flask import Flask, jsonify, request

app = Flask(__name__)
todos = []

@app.route("/")
def home():
    return jsonify(message="To-Do App is running", version="v1.0")

@app.route("/health")
def health():
    return jsonify(status="healthy"), 200

@app.route("/todos", methods=["GET"])
def get_todos():
    return jsonify(todos)

@app.route("/todos", methods=["POST"])
def add_todo():
    data = request.get_json()
    todo = {"id": len(todos) + 1, "task": data.get("task")}
    todos.append(todo)
    return jsonify(todo), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
