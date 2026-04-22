from shared.infrastructure import db


class AnnouncementDB(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    cta_label = db.Column(db.String(80), nullable=True)
    cta_url = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text("0"))
    published_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )

    creator = db.relationship("UserDB", backref="created_announcements")