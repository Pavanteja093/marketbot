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


def research_dashboard():

    factor_research()

    strategy_research()

    factor_performance()

    compare_models()

    score_distribution()

    build_ml_dataset()

    split_dataset()

    feature_importance()

    feature_stability()

    feature_drift()

    signal_quality()

    dataset_health()

    explanation_examples()

    regime_performance()

    top_vs_bottom()

    outlier_detector()

    factor_drift()

    rank_stability()

    walk_forward_validation()

    prediction_calibration()

    rolling_performance()

    feature_selector()

    optimize_weights()

    model_version()

    champion_model()

    weight_history()

    weight_drift()

if __name__ == "__main__":
    research_dashboard()