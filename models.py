from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}
    school_id = db.Column(db.String(), primary_key=True)
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    email = db.Column(db.String(), unique=True)
    password = db.Column(db.String())
    role = db.Column(db.String(), nullable=False)
    picture = db.Column(db.LargeBinary())
    hours = db.Column(db.Numeric())
    form = db.Column(db.String(), nullable=False)


class Award(db.Model):
    __tablename__ = 'award'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    threshold = db.Column(db.Integer)
    colour = db.Column(db.String)


class Status(db.Model):
    __tablename__ = 'status'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String, unique=True, nullable=False)


class ServiceHour(db.Model):
    __tablename__ = 'service_hours'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('user.school_id'), nullable=False) # noqa
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    hours = db.Column(db.Integer)
    date = db.Column(db.Integer)
    description = db.Column(db.Text)
    status = db.Column(db.Integer, db.ForeignKey('status.id'))
    time = db.Column(db.Integer)
    log_time = db.Column(db.Integer)
    staff = db.Column(db.String, db.ForeignKey('user.school_id'))

    # Relationships
    user = db.relationship('User', backref='service_hours', foreign_keys=[user_id]) # noqa
    staff_user = db.relationship('User', foreign_keys=[staff])
    group = db.relationship('Group', backref='service_hours')


class Group(db.Model):
    __tablename__ = 'group'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    staff = db.Column(db.String, db.ForeignKey('user.school_id'))


class UserRole(db.Model):
    __tablename__ = 'user_role'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)


def init_models(app):
    db.init_app(app)
