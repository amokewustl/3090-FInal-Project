"""
app.py - Flask application for redistricting
"""
from flask import Flask, render_template, request, jsonify, send_file
import numpy as np
import io
import base64
import traceback
from database import init_db, add_user_plan, get_all_plans, delete_user_plan, get_user_plans
from redistricting_logic import (
    validate_districts, 
    calculate_district_winners,
    generate_consensus_maps,
    generate_consensus_figure,
    get_compactness_report,
    rank_plans_by_compactness
)
from Plans import neutral_plans, hearts_representative_plans

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Initialize database on startup
try:
    with app.app_context():
        init_db()
    print("✅ Database initialized successfully!")
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    traceback.print_exc()

# Vote distribution (0=Club, 1=Heart)
VOTE_GRID = [
    [0, 0, 1, 1, 1],
    [1, 1, 1, 0, 1],
    [0, 0, 1, 0, 1],
    [0, 0, 0, 1, 0],
    [0, 1, 0, 1, 0]
]

@app.route('/')
def index():
    """Render main page"""
    try:
        return render_template('index.html', vote_grid=VOTE_GRID)
    except Exception as e:
        print(f"❌ Error rendering index: {e}")
        traceback.print_exc()
        return f"Error: {str(e)}", 500


@app.route('/api/validate', methods=['POST'])
def validate():
    """Validate a district plan"""
    data = request.json
    districts = np.array(data['districts'])
    
    is_valid, errors = validate_districts(districts)
    
    if is_valid:
        winners = calculate_district_winners(districts, VOTE_GRID)
        hearts_won = sum(1 for w in winners.values() if w == 'Hearts')
        clubs_won = sum(1 for w in winners.values() if w == 'Clubs')
        
        return jsonify({
            'valid': True,
            'winners': winners,
            'hearts_won': hearts_won,
            'clubs_won': clubs_won
        })
    else:
        return jsonify({
            'valid': False,
            'errors': errors
        })

@app.route('/api/submit', methods=['POST'])
def submit_plan():
    """Submit a new redistricting plan"""
    data = request.json
    districts = data['districts']
    plan_type = data['type']  # 'neutral' or 'hearts_representative'
    user_name = data.get('name', 'Anonymous')
    
    # Validate before submission
    is_valid, errors = validate_districts(np.array(districts))
    if not is_valid:
        return jsonify({'success': False, 'errors': errors}), 400
    
    # Add to database
    plan_id = add_user_plan(districts, plan_type, user_name)
    
    return jsonify({
        'success': True,
        'plan_id': plan_id,
        'message': 'Plan submitted successfully!'
    })

@app.route('/api/plans/user')
def get_user_plans_route():
    """Get all user-submitted plans"""
    plans = get_user_plans()
    return jsonify({'plans': plans})

@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """Delete a user plan"""
    success = delete_user_plan(plan_id)
    if success:
        return jsonify({'success': True, 'message': 'Plan deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Plan not found'}), 404

@app.route('/api/consensus')
def get_consensus():
    """Generate and return consensus maps"""
    # Get all plans (base + user)
    all_plans_data = get_all_plans()
    
    # Separate by type
    all_plans = [np.array(p['districts']) for p in all_plans_data]
    neutral = [np.array(p['districts']) for p in all_plans_data if p['type'] == 'neutral']
    hearts = [np.array(p['districts']) for p in all_plans_data if p['type'] == 'hearts_representative']
    
    # Generate consensus maps
    consensus_all = generate_consensus_maps(all_plans)
    consensus_neutral = generate_consensus_maps(neutral) if neutral else None
    consensus_hearts = generate_consensus_maps(hearts) if hearts else None
    
    # Generate figures as base64 images
    fig_all = generate_consensus_figure(consensus_all, f"All Plans (n={len(all_plans)})")
    fig_neutral = generate_consensus_figure(consensus_neutral, f"Neutral Plans (n={len(neutral)})") if consensus_neutral is not None else None
    fig_hearts = generate_consensus_figure(consensus_hearts, f"Hearts Plans (n={len(hearts)})") if consensus_hearts is not None else None
    
    # Get compactness metrics for consensus maps
    compactness_all = get_compactness_report(consensus_all) if consensus_all is not None else None
    compactness_neutral = get_compactness_report(consensus_neutral) if consensus_neutral is not None else None
    compactness_hearts = get_compactness_report(consensus_hearts) if consensus_hearts is not None else None
    
    return jsonify({
        'all_plans': fig_all,
        'neutral_plans': fig_neutral,
        'hearts_plans': fig_hearts,
        'counts': {
            'total': len(all_plans),
            'neutral': len(neutral),
            'hearts': len(hearts)
        },
        'compactness': {
            'all': compactness_all,
            'neutral': compactness_neutral,
            'hearts': compactness_hearts
        }
    })

@app.route('/api/rankings')
def get_rankings():
    """Get all plans ranked by compactness"""
    all_plans_data = get_all_plans()
    rankings = rank_plans_by_compactness(all_plans_data)
    
    return jsonify({
        'rankings': rankings
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)