"""PetCare 宠物医院管理系统 - Flask 后端主入口"""

import os
from flask import Flask, jsonify, send_from_directory

try:
    import config_api
except ImportError:
    pass

from database.db import init_database
from config import Config
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.pet_routes import pet_bp
from routes.medical_routes import medical_bp
from routes.vaccination_routes import vaccine_bp
from routes.drug_routes import drug_bp
from routes.ai_routes import ai_bp
from routes.soap_routes import soap_bp

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["JSON_AS_ASCII"] = False

    init_database()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pet_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(vaccine_bp)
    app.register_blueprint(drug_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(soap_bp)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        if path.startswith("api/"):
            return jsonify({"error": "接口不存在"}), 404
        file_path = os.path.join(STATIC_DIR, path) if path else os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(file_path):
            return send_from_directory(STATIC_DIR, path or "index.html")
        return send_from_directory(STATIC_DIR, "index.html")

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "接口不存在"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "服务器内部错误"}), 500

    return app


if __name__ == "__main__":
    print("=" * 50)
    print("  PetCare 宠物医院管理系统")
    print("=" * 50)
    print("正在初始化数据库...")
    print("数据库初始化完成。")
    app = create_app()
    print(f"服务器启动: http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
