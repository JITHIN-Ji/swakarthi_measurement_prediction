from flask import request, jsonify, Blueprint
import pandas as pd
from datetime import datetime

from config import logger, MEASUREMENTS_FILE

import model_loader 

from utils import (
    load_measurements,
    save_measurements,
    calculate_css_measurements,
    validate_input,
    get_brand_measurements,
    calculate_additional_measurements, 
    validate_measurements_format,
    convert_gender
)

api = Blueprint('api', __name__)

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    measurements_data = load_measurements()
    
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_loader.model is not None,
        'total_users': len(measurements_data),
        'measurements_file': MEASUREMENTS_FILE
    })

@api.route('/predict-measurements', methods=['POST'])
def predict_measurements():
    """Predict body measurements based on input parameters."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        
        is_valid, message = validate_input(data)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        if model_loader.model is None:
            return jsonify({'error': 'Model not initialized'}), 500
        
        parent_id = str(data['parent_id'])
        child_id = str(data['child_id'])
        age = float(data['age'])
        gender = convert_gender(data['gender'])  
        weight = float(data['weight'])
        height = float(data['height'])
        brand = data.get("brand")  # Optional brand parameter

        measurements = {}

        # ✅ Case 1: Brand available
        if brand:
            brand_meas = get_brand_measurements(brand, age, 'male' if gender == 1 else 'female')
            if brand_meas:
                measurements.update(brand_meas)

        # ✅ Case 2: No brand OR brand not found → fallback ML prediction
        if not measurements:
            input_data = pd.DataFrame([{
                "Age": age,
                "Gender": gender,
                "Height_cm": height,
                "Weight_kg": weight
            }])

            prediction = model_loader.model.predict(input_data)[0]
            waist, hip, bicep, wrist = prediction[:4]

            measurements.update({
                'Waist': float(round(waist, 2)),
                'Hip': float(round(hip, 2)),
                'Bicep': float(round(bicep, 2)),
                'Wrist': float(round(wrist, 2))
            })

    
        chest, shoulder, sleeve = calculate_css_measurements(age, 'male' if gender == 1 else 'female', height)

        
        if "Chest" not in measurements:
            measurements["Chest"] = float(round(chest, 2))

        measurements.update({
            "Shoulder": float(round(shoulder, 2)),
            "Sleeve": float(round(sleeve, 2))
        })

        
        synthetic = calculate_additional_measurements(age, 'male' if gender == 1 else 'female', height, chest)
        measurements.update(synthetic)

        
        measurements_data = load_measurements()
        if parent_id not in measurements_data:
            measurements_data[parent_id] = {}
        
        user_data = {
            'parent_id': parent_id,
            'child_id': child_id,
            'input_parameters': {
                'age': age,
                'gender': 'male' if gender == 1 else 'female',
                'weight': weight,
                'height': height,
                'brand': brand if brand else None
            },
            'measurements_cm': measurements,
            'measurements_inches': {key: round(value / 2.54, 2) for key, value in measurements.items()},
            'prediction_timestamp': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'is_predicted': True,
            'is_manually_updated': False
        }
        
        measurements_data[parent_id][child_id] = user_data
        if save_measurements(measurements_data):
            logger.info(f"Measurements saved for {parent_id}/{child_id}")
        else:
            logger.error(f"Failed to save measurements for {parent_id}/{child_id}")
        
        return jsonify({
            'success': True,
            'parent_id': parent_id,
            'child_id': child_id,
            'measurements_cm': measurements,
            'measurements_inches': {
                key: round(value / 2.54, 2) for key, value in measurements.items()
            },
            'message': 'Measurements predicted and saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in prediction: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/update-measurements', methods=['PUT'])
def update_measurements():
    """Update measurements for a specific child under a parent."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()

        is_valid, message = validate_input(data, for_update=True)
        if not is_valid:
            return jsonify({'error': message}), 400

        parent_id = str(data['parent_id'])
        child_id = str(data['child_id'])

        measurements_data = load_measurements()

        if parent_id not in measurements_data or child_id not in measurements_data[parent_id]:
            return jsonify({'error': f'Child {child_id} under parent {parent_id} not found. Please make a prediction first.'}), 404

        user_data = measurements_data[parent_id][child_id]

        if 'measurements' in data:
            is_valid, message = validate_measurements_format(data['measurements'])
            if not is_valid:
                return jsonify({'error': message}), 400

            for key, value in data['measurements'].items():
                user_data['measurements_cm'][key] = round(float(value), 2)

            user_data['measurements_inches'] = {
                key: round(value / 2.54, 2) for key, value in user_data['measurements_cm'].items()
            }

            user_data['last_updated'] = datetime.now().isoformat()
            user_data['is_manually_updated'] = True

        if save_measurements(measurements_data):
            logger.info(f"Measurements updated for {parent_id}/{child_id}")
        else:
            logger.error(f"Failed to update measurements for {parent_id}/{child_id}")
            return jsonify({'error': 'Failed to save updated measurements'}), 500

        return jsonify({
            'success': True,
            'parent_id': parent_id,
            'child_id': child_id,
            'measurements_cm': user_data['measurements_cm'],
            'measurements_inches': user_data['measurements_inches'],
            'message': 'Measurements updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating measurements: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@api.route('/get-measurements/<parent_id>/<child_id>', methods=['GET'])
def get_measurements(parent_id, child_id):
    """Get measurements for a specific child under a parent."""
    try:
        measurements_data = load_measurements()

        if parent_id not in measurements_data or child_id not in measurements_data[parent_id]:
            return jsonify({'error': f'Child {child_id} under parent {parent_id} not found'}), 404

        user_data = measurements_data[parent_id][child_id]

        return jsonify({
            'success': True,
            'parent_id': parent_id,
            'child_id': child_id,
            'input_parameters': user_data.get('input_parameters', {}),
            'measurements_cm': user_data.get('measurements_cm', {}),
            'measurements_inches': user_data.get('measurements_inches', {}),
            'prediction_timestamp': user_data.get('prediction_timestamp', ''),
            'last_updated': user_data.get('last_updated', ''),
            'is_predicted': user_data.get('is_predicted', False),
            'is_manually_updated': user_data.get('is_manually_updated', False)
        })

    except Exception as e:
        logger.error(f"Error retrieving measurements: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500