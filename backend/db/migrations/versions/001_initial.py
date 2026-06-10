"""Initial schema for jobs, scenes, and videos.

Revision ID: 001_initial
Revises:
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"jobs",
		sa.Column("id", sa.String(length=64), primary_key=True),
		sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
		sa.Column("input_filename", sa.String(length=255), nullable=False, server_default=""),
		sa.Column("max_scenes", sa.Integer(), nullable=False, server_default="15"),
		sa.Column("error", sa.Text(), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
	)
	op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
	op.create_index("ix_jobs_created_at", "jobs", ["created_at"], unique=False)

	op.create_table(
		"scenes",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
		sa.Column("scene_index", sa.Integer(), nullable=False),
		sa.Column("narration", sa.Text(), nullable=False, server_default=""),
		sa.Column("svg_markup", sa.Text(), nullable=False, server_default=""),
		sa.Column("metaphor_hint", sa.Text(), nullable=False, server_default=""),
		sa.Column("audio_path", sa.String(length=512), nullable=False, server_default=""),
		sa.Column("audio_duration_ms", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("draw_duration_ms", sa.Integer(), nullable=False, server_default="0"),
	)
	op.create_index("ix_scenes_job_id", "scenes", ["job_id"], unique=False)
	op.create_index("ix_scenes_job_scene", "scenes", ["job_id", "scene_index"], unique=False)

	op.create_table(
		"videos",
		sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
		sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
		sa.Column("file_path", sa.String(length=512), nullable=False, server_default=""),
		sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
		sa.UniqueConstraint("job_id", name="uq_videos_job_id"),
	)
	op.create_index("ix_videos_job_id", "videos", ["job_id"], unique=True)


def downgrade() -> None:
	op.drop_index("ix_videos_job_id", table_name="videos")
	op.drop_table("videos")

	op.drop_index("ix_scenes_job_scene", table_name="scenes")
	op.drop_index("ix_scenes_job_id", table_name="scenes")
	op.drop_table("scenes")

	op.drop_index("ix_jobs_created_at", table_name="jobs")
	op.drop_index("ix_jobs_status", table_name="jobs")
	op.drop_table("jobs")
