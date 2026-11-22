from flask import Blueprint, jsonify, abort
from . import services

projects_bp = Blueprint("projects", __name__)


@projects_bp.get("")
def list_projects():
    return jsonify(services.get_all_projects())


@projects_bp.get("/<int:project_id>")
def get_project(project_id):
    project = services.get_project_by_id(project_id)
    if not project:
        abort(404, description="Project not found")
    return jsonify(project)