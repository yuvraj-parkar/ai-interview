from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config import Config
from backend.models import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    init_db(app)

    from backend.routes.auth import auth_bp
    from backend.routes.interviews import interviews_bp
    from backend.routes.ai import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(ai_bp)

    @app.route("/", methods=["GET"])
    def health():
        return jsonify({"status": "AI Interview v2 Backend", "version": "2.0"})

    return app
