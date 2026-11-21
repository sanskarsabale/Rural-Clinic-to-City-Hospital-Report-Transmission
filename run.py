"""
RuralLink Application Entry Point
Run with: python run.py
Or for production: gunicorn "app:create_app()"
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
