from flask import Flask, jsonify
from model_loader import initialize_model
from routes import api 
from chatbot_routes import chatbot_api
from config import logger
from flask_cors import CORS

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    initialize_model()
    
    # Register the blueprint, which contains all our routes
    app.register_blueprint(api)
    logger.info("API routes registered.")

    app.register_blueprint(chatbot_api)
    logger.info("Chatbot API routes registered.")


    # Define global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405

    return app
app = create_app()

if __name__ == '__main__':
    logger.info("Starting the Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)