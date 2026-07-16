"""PetCare 宠物医院管理系统 - Flask 后端主入口"""

from flask import Flask, jsonify

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


def init_knowledge_base():
    """启动时自动加载中英双语知识库"""
    try:
        from services.rag_service import get_knowledge_base
        for lang, label in [("en", "英文"), ("zh", "中文")]:
            kb = get_knowledge_base(lang)
            if kb.is_ready:
                kb.load()
                stats = kb.get_stats()
                print(f"[RAG] {label}知识库已加载 | 文件: {len(set(m.get('source','') for m in kb._chunk_meta))} | "
                      f"文本块: {stats.get('total_chunks',0)} | "
                      f"页数: {stats.get('total_pages',0)}")
            else:
                print(f"[RAG] {label}知识库索引未构建")
    except Exception as e:
        print(f"[RAG] 知识库加载失败: {e}")


def create_app() -> Flask:
    app = Flask(__name__)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pet_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(vaccine_bp)
    app.register_blueprint(drug_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(soap_bp)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "接口不存在"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "请求方法不允许"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "服务器内部错误"}), 500

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

    print("正在加载知识库...")
    init_knowledge_base()

    app = create_app()
    print(f"服务器启动: http://{Config.HOST}:{Config.PORT}")
    print("API 健康检查: http://{Config.HOST}:{Config.PORT}/api/health")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
