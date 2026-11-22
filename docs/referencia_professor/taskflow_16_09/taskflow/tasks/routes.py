from flask import Blueprint, jsonify, request
from . import services

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.get("")
def list_tasks():
    project_id = request.args.get("project_id", type=int)
    if project_id:
        return jsonify(services.get_tasks_by_project(project_id))
    return jsonify(services.get_all_tasks())