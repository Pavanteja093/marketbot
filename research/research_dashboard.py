from research.factor_research import factor_research
from research.strategy_research import strategy_research
from research.factor_performance import factor_performance
from research.model_comparison import compare_models
from research.ml_dataset import build_ml_dataset
from research.feature_importance import feature_importance
from research.train_test_split import split_dataset
from research.score_distribution import score_distribution
from research.feature_stability import feature_stability
from research.feature_drift import feature_drift
from research.signal_quality import signal_quality
from research.dataset_health import dataset_health
from research.explanation_examples import explanation_examples
from research.regime_performance import regime_performance
from research.top_vs_bottom import top_vs_bottom
from research.outlier_detector import outlier_detector
from research.factor_drift import factor_drift
from research.rank_stability import rank_stability
from research.walk_forward import walk_forward_validation
from research.prediction_calibration import prediction_calibration
from research.rolling_performance import rolling_performance
from research.feature_selector import feature_selector
from research.weight_optimizer import optimize_weights
from research.model_version import model_version
from research.champion_model import champion_model
from research.weight_history import weight_history
from research.weight_drift import weight_drift
from research.champion_report import champion_report
from research.challenger_report import challenger_report
from research.model_accuracy import update_accuracy
from research.score_drift import score_drift
from research.model_registry_health import registry_health
from research.feature_consistency import consistency
from research.confidence_calibration import confidence_bins
from research.model_scorecard import model_scorecard
from research.prediction_accuracy import prediction_accuracy
from research.validate_predictions import validate_predictions
from research.update_weights import update_weights
from research.weight_change_report import weight_change_report
from research.model_progress import model_progress
from research.generate_challenger import generate_challenger
from research.evolution_statistics import evolution_statistics
from research.challenger_statistics import challenger_statistics
from research.factor_registry import factor_registry
from research.evolution_history import save_evolution
from research.model_battle import model_battle
from research.portfolio_simulator import portfolio_simulator    
from analytics.portfolio_engine import portfolio_engine
from research.learning_engine import learning_engine
from research.factor_reliability import factor_reliability


def research_dashboard():

    # ==================================
    # Phase 1 : Data Quality
    # ==================================

    factor_reliability()

    dataset_health()

    score_distribution()

    feature_stability()

    feature_drift()

    score_drift()

    factor_drift()

    outlier_detector()

    signal_quality()


    # ==================================
    # Phase 2 : Research
    # ==================================

    factor_research()

    factor_registry()

    factor_performance()

    strategy_research()

    top_vs_bottom()

    regime_performance()

    rank_stability()


    # ==================================
    # Phase 3 : Machine Learning
    # ==================================

    build_ml_dataset()

    split_dataset()

    feature_selector()

    feature_importance()

    compare_models()

    walk_forward_validation()

    rolling_performance()


    # ==================================
    # Phase 4 : Prediction Evaluation
    # ==================================

    validate_predictions()

    prediction_accuracy()

    prediction_calibration()

    confidence_bins()

    learning_engine()


    # ==================================
    # Phase 5 : Adaptive Learning
    # ==================================

    optimize_weights()

    update_weights()

    weight_history()

    weight_drift()

    generate_challenger()

    weight_change_report()


    # ==================================
    # Phase 6 : Model Registry
    # ==================================

    model_version()

    update_accuracy("MarketBot V1",0.61)

    champion_model()

    champion_report()

    model_battle()

    portfolio_simulator()

    portfolio_engine()

    evolution_statistics()

    save_evolution()

    challenger_report()

    challenger_statistics()
    
    registry_health()

    model_scorecard()

    model_progress()


    # ==================================
    # Phase 7 : Explainability
    # ==================================

    explanation_examples()

if __name__ == "__main__":
    research_dashboard()