"""PetCare 宠物医院管理系统 - Flask 后端主入口"""

from flask import Flask, jsonify
from database.db import init_database
from config import Config
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.pet_routes import pet_bp
from routes.medical_routes import medical_bp
from routes.vaccination_routes import vaccine_bp
from routes.drug_routes import drug_bp
from routes.ai_routes import ai_bp


def create_app() -> Flask:
    app = Flask(__name__)

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pet_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(vaccine_bp)
    app.register_blueprint(drug_bp)
    app.register_blueprint(ai_bp)

    # 全局错误处理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "接口不存在"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "服务器内部错误"}), 500

    # 健康检查
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "PetCare Veterinary API"}), 200

    return app


if __name__ == "__main__":
    print("=" * 50)
    print("  PetCare 宠物医院管理系统 v2.0")
    print("=" * 50)
    print("正在初始化数据库...")
    init_database()
    print("数据库初始化完成。")

    app = create_app()
    print(f"服务器启动: http://{Config.HOST}:{Config.PORT}")
    print("API 健康检查: http://{Config.HOST}:{Config.PORT}/api/health")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
