def register_blueprints(app):
    from .auth import bp as auth
    from .schools import bp as schools
    from .admissions import bp as admissions
    from .students import bp as students
    from .academics import bp as academics
    from .finance import bp as finance
    from .announcements import bp as announcements
    from .teachers import bp as teachers
    from .parents import bp as parents
    from .apex import bp as apex
    for bp in (auth, schools, admissions, students, academics, finance, announcements, teachers, parents, apex):
        versioned_prefix = bp.url_prefix.replace("/api", "/api/v1", 1)
        app.register_blueprint(bp, url_prefix=versioned_prefix, name=f"{bp.name}_v1")
        app.register_blueprint(bp, name=f"{bp.name}_legacy")
