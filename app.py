from flask import Flask, jsonify, request
from model_loader import initialize_model
from routes import api 
from chatbot_routes import chatbot_api
from config import logger
from flask_cors import CORS

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Enhanced CORS configuration
    CORS(app, 
         resources={r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
         }})
    
    initialize_model()
    
    # Root route for health check
    @app.route('/', methods=['GET', 'OPTIONS'])
    def home():
        return jsonify({
            'status': 'success',
            'message': 'Swakarthi Measurement Prediction API is running',
            'version': '1.0'
        }), 200
    
    # Register blueprints
    app.register_blueprint(api)
    logger.info("API routes registered.")
    app.register_blueprint(chatbot_api)
    logger.info("Chatbot API routes registered.")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405
    
    return app

app = create_app()

if __name__ == '__main__':
    logger.info("Starting the Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
