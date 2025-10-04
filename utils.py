import json
import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from config import logger, MEASUREMENTS_FILE

def load_measurements():
    """Load measurements from JSON file."""
    if os.path.exists(MEASUREMENTS_FILE):
        try:
            with open(MEASUREMENTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode {MEASUREMENTS_FILE}. Starting with empty data.")
            return {}
    return {}

def save_measurements(measurements_data):
    """Save measurements to JSON file."""
    try:
        with open(MEASUREMENTS_FILE, 'w') as f:
            json.dump(measurements_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving measurements: {str(e)}")
        return False

def calculate_css_measurements(age, gender_str, height):
    """Calculate Chest, Shoulder, and Sleeve using formulas based on age, gender, and height."""
    if age < 2:
        chest = height * 0.51
    elif age < 6:
        chest = height * 0.49
    else:
        chest = height * 0.47

    if gender_str == "male":
        shoulder = height * (0.22 if age < 6 else 0.23)
    else:
        shoulder = height * (0.21 if age < 6 else 0.22)

    if age < 2:
        sleeve = height * 0.28
    elif age < 6:
        sleeve = height * 0.30
    else:
        sleeve = height * 0.32

    return chest, shoulder, sleeve


def parse_range(value):
    """Convert '71–78' → average(71,78). Handle single numbers too."""
    if pd.isna(value):
        return None
    value = str(value).strip()
    match = re.findall(r"\d+\.?\d*", value)
    if not match:
        return None
    nums = list(map(float, match))
    return np.mean(nums) if len(nums) > 1 else nums[0]

def age_matches(age_str, target_age):
    """Check if target_age falls into the dataset's Age (Years) field."""
    if pd.isna(age_str):
        return False
    age_str = str(age_str).strip()
    
    # Handle ranges like '10&11' or '4&5'
    if "&" in age_str:
        ages = [int(a) for a in re.findall(r"\d+", age_str)]
        return int(target_age) in ages
    
    # Handle ranges like '104–110'
    if "–" in age_str or "-" in age_str:
        nums = [int(a) for a in re.findall(r"\d+", age_str)]
        if len(nums) == 2:
            return nums[0] <= int(target_age) <= nums[1]
    
    # Handle single number like '120'
    if age_str.isdigit():
        return int(age_str) == int(target_age)
    
    return False


def get_brand_measurements(brand, age, gender, dataset_path="Copy of brandsize(1).csv"):
    """
    Fetch measurements for a specific brand, age, and gender.
    Handles H&M gender markers (B/G) and falls back if missing.
    """
    try:
        df = pd.read_csv(dataset_path, encoding='latin1')
    except FileNotFoundError:
        logger.error(f"Dataset file not found at: {dataset_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading dataset '{dataset_path}': {e}") 
        return None

    logger.debug(f"Input brand: {brand}, age: {age}, gender: {gender}")

    gender_str_lower = gender.lower()
    gender_marker = "B" if gender_str_lower in ["male", "m", "boy"] else "G"

    # Extract gender marker from brand for H&M
    if "h&m" in brand.lower():
        df['GenderMarker'] = df['Brand'].str.extract(r'\((B|G)\)')
        # Filter H&M rows
        filtered_by_brand = df[df['Brand'].str.contains("h&m", case=False, na=False)]
        # Filter by gender marker
        filtered_by_gender = filtered_by_brand[filtered_by_brand['GenderMarker'] == gender_marker]

        # If no gender-specific row exists, fallback to any H&M row for that age
        filtered = filtered_by_gender if not filtered_by_gender.empty else filtered_by_brand
    else:
        # Other brands: filter by brand only
        filtered = df[df['Brand'].str.contains(brand, case=False, na=False)]

    # Filter by age
    filtered_by_age = filtered[filtered['Age (Years)'].apply(lambda x: age_matches(x, age))]
    logger.debug(f"DataFrame after age filter for {age}:\n{filtered_by_age.to_string()}")

    if filtered_by_age.empty:
        logger.warning(f"No matching measurements found for brand '{brand}' and age {age}.")
        return None

    row = filtered_by_age.iloc[0]
    logger.debug(f"Found matching row:\n{row.to_string()}")

    measurements = {
        "Chest": parse_range(row.get("Chest (cm)", None)),
        "Waist": parse_range(row.get("Waist (cm)", None)),
        "Hip": parse_range(row.get("Hips (cm)", None))
    }
    logger.debug(f"Parsed measurements: {measurements}")
    return measurements

def calculate_additional_measurements(age, gender_str, height,chest):
    """
    Adjust synthetic measurements to realistic child proportions (ages 1–15).
    All lengths are approximate and measured as actual garment lengths.
    """
    
    inseam = height * (0.38 if age <= 5 else 0.42 if age <= 10 else 0.45)
    toplength = height * (0.35 if age <= 5 else 0.38 if age <= 10 else 0.40)
    kurtalength = height * (0.40 if age <= 5 else 0.43 if age <= 10 else 0.46)
    pant_length = inseam + height * 0.05
    knee_length = height * 0.26 if age <= 5 else height * 0.27 if age <= 10 else height * 0.28
    midi_length = height * 0.35 if age <= 5 else height * 0.40 if age <= 10 else height * 0.45
    ankle_length = height * 0.48 if age <= 5 else height * 0.50 if age <= 10 else height * 0.55
    maxilength = height * 0.55 if age <= 5 else height * 0.58 if age <= 10 else height * 0.60
    armhole = height * 0.12
    chest = height * 0.52 
    neck_depth_front = chest * 0.115  # approx 11.5% of chest
    neck_depth_back  = chest * 0.07   # approx 7% of chest
    neck_depth_front = max(neck_depth_front, 2.5)
    neck_depth_back  = max(neck_depth_back, 1.5)


    return {
        'Inseam': round(inseam, 2),
        'Armhole': round(armhole, 2),
        'TopLength': round(toplength, 2),
        'KurtaLength': round(kurtalength, 2),
        'PantLength': round(pant_length, 2),
        'KneeLength': round(knee_length, 2),
        'MidiLength': round(midi_length, 2),
        'AnkleLength': round(ankle_length, 2),
        'MaxiLength': round(maxilength, 2),
        'NeckDepthBack': round(neck_depth_back, 2),
        'NeckDepthFront': round(neck_depth_front, 2),
    }


def validate_input(data, for_update=False):
    required_fields = ['parent_id', 'child_id']
    if not for_update:
        required_fields.extend(['height', 'weight', 'gender', 'age'])

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    if not isinstance(data['parent_id'], str) or not data['parent_id'].strip():
        return False, "Parent ID must be a non-empty string"
    if not isinstance(data['child_id'], str) or not data['child_id'].strip():
        return False, "Child ID must be a non-empty string"

    # Skip other validations for update requests with only measurements
    if for_update and len(data) == 2 and 'measurements' in data:
        return validate_measurements_format(data['measurements'])
    
    if not for_update:
        # Validate data types and ranges
        try:
            age = float(data['age'])
            if not (3 <= age <= 18):
                return False, "Age must be between 3 and 18 years"
        except (ValueError, TypeError):
            return False, "Age must be a valid number"
        
        try:
            weight = float(data['weight'])
            if not (10.0 <= weight <= 120.0):
                return False, "Weight must be between 10.0 and 120.0 kg"
        except (ValueError, TypeError):
            return False, "Weight must be a valid number"
        
        try:
            height = float(data['height'])
            if not (80.0 <= height <= 220.0):
                return False, "Height must be between 80.0 and 220.0 cm"
        except (ValueError, TypeError):
            return False, "Height must be a valid number"
        
        # Validate gender
        gender = data['gender']
        if isinstance(gender, str):
            gender_lower = gender.lower()
            if gender_lower not in ['male', 'female', 'm', 'f']:
                return False, "Gender must be 'male', 'female', 'm', or 'f'"
        elif isinstance(gender, int):
            if gender not in [1, 2]:
                return False, "Gender must be 1 (male) or 2 (female)"
        else:
            return False, "Gender must be a string or integer"
    
    return True, "Valid"

def validate_measurements_format(measurements):
    """Validate measurements format for updates."""
    if not isinstance(measurements, dict):
        return False, "Measurements must be a dictionary"
    
    valid_measurement_keys = ['Waist', 'Hip', 'Bicep', 'Neck', 'Wrist', 'Chest', 'Shoulder', 'Sleeve']

    for key, value in measurements.items():
        if key not in valid_measurement_keys:
            return False, f"Invalid measurement key: {key}. Valid keys are: {', '.join(valid_measurement_keys)}"
        
        try:
            float_value = float(value)
            if float_value <= 0:
                return False, f"Measurement {key} must be a positive number"
        except (ValueError, TypeError):
            return False, f"Measurement {key} must be a valid number"
    
    return True, "Valid"

def convert_gender(gender):
    """Convert gender to numeric format."""
    if isinstance(gender, str):
        gender_lower = gender.lower()
        if gender_lower in ['male', 'm']:
            return 1
        elif gender_lower in ['female', 'f']:
            return 2
    elif isinstance(gender, int):
        return gender
    return 1  # Default to male