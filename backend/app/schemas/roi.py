"""SupplyPrescript — Decision ROI Engine Schemas (Day 20)
=======================================================
Pydantic schemas for single-decision ROI analytics, decision success evaluation,
and portfolio-level ROI aggregations.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


# Decision Success Evaluation Types
DecisionSuccessType = Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILURE", "PENDING_REVIEW"]
CostPerformanceType = Literal["BETTER_THAN_PREDICTED", "ON_TARGET", "WORSE_THAN_PREDICTED", "UNKNOWN"]
DeliveryPerformanceType = Literal["BETTER_THAN_PREDICTED", "ON_TARGET", "WORSE_THAN_PREDICTED", "UNKNOWN"]
ConstraintComplianceType = Literal["PASS", "FAIL", "UNKNOWN"]
QuantityPerformanceType = Literal["MET_TARGET", "PARTIAL_FULFILLMENT", "EXCEEDED_TARGET", "BELOW_TARGET", "UNKNOWN"]
DataCompletenessType = Literal["COMPLETE", "PARTIAL", "INSUFFICIENT"]
ROIStatusType = Literal["CALCULATED", "UNAVAILABLE"]


class CostROIDetails(BaseModel):
    """Detailed financial variance and money saved metrics."""
    predicted_cost: Optional[str] = Field(None, description="Original predicted cost formatted as string")
    actual_cost: Optional[str] = Field(None, description="Verified actual cost from PostgreSQL outcome")
    cost_difference: Optional[str] = Field(None, description="actual_cost - predicted_cost (positive = overrun)")
    cost_variance_percentage: Optional[float] = Field(None, description="((actual_cost - predicted_cost) / predicted_cost) * 100")
    money_saved_vs_prediction: Optional[str] = Field(None, description="predicted_cost - actual_cost (positive = savings vs forecast)")
    baseline_cost: Optional[str] = Field(None, description="Documented baseline cost for shipment if available")
    money_saved_vs_baseline: Optional[str] = Field(None, description="baseline_cost - actual_cost (verified savings vs baseline)")

    model_config = ConfigDict(extra="ignore")


class DeliveryROIDetails(BaseModel):
    """Delivery and delay comparison metrics."""
    predicted_delay: Optional[float] = Field(None, description="Predicted delay in days from decision record")
    actual_delay: Optional[float] = Field(None, description="Verified actual delay in days from outcome record")
    delay_difference: Optional[float] = Field(None, description="actual_delay - predicted_delay (positive = worse than predicted)")

    model_config = ConfigDict(extra="ignore")


class ROIMetrics(BaseModel):
    """Return on Investment (ROI) calculation breakdown."""
    investment_cost: Optional[str] = Field(None, description="Documented positive incremental investment denominator")
    net_benefit: Optional[str] = Field(None, description="baseline_cost - actual_cost - additional_costs")
    roi_percentage: Optional[float] = Field(None, description="(net_benefit / investment_cost) * 100")
    status: ROIStatusType = Field(..., description="CALCULATED or UNAVAILABLE")
    reason: str = Field(..., description="Detailed explanation of calculation or why ROI is unavailable")

    model_config = ConfigDict(extra="ignore")


class DecisionEvaluation(BaseModel):
    """Multi-dimensional evaluation of decision outcome success."""
    decision_success: DecisionSuccessType = Field(..., description="Overall decision outcome status")
    cost_performance: CostPerformanceType = Field(..., description="Cost classification vs prediction")
    delivery_performance: DeliveryPerformanceType = Field(..., description="Delivery classification vs prediction")
    constraint_compliance: ConstraintComplianceType = Field(..., description="Hard business constraint status")
    quantity_performance: QuantityPerformanceType = Field(..., description="Quantity fulfillment vs target")
    data_completeness: DataCompletenessType = Field(..., description="Outcome data completeness")
    success_reason: str = Field(..., description="Human-readable explanation of decision evaluation")
    policy_is_provisional: bool = Field(True, description="Indicates whether decision success thresholds are provisional")

    model_config = ConfigDict(extra="ignore")


class DecisionROIResponse(BaseModel):
    """Comprehensive single-decision ROI and success report."""
    decision_id: str = Field(..., description="Unique decision identifier")
    shipment_id: Optional[str] = Field(None, description="Target shipment identifier")
    currency: str = Field("USD", description="Currency code for financial metrics")
    cost: CostROIDetails = Field(..., description="Financial comparison metrics")
    delivery: DeliveryROIDetails = Field(..., description="Delivery delay metrics")
    roi: ROIMetrics = Field(..., description="Return on investment metrics")
    decision_evaluation: DecisionEvaluation = Field(..., description="Decision success evaluation breakdown")
    calculation_version: str = Field("1.0", description="ROI engine calculation methodology version")
    calculation_method: str = Field(..., description="Detailed description of applied formulas and rules")
    notes: List[str] = Field(default_factory=list, description="Operational notes and edge-case warnings")

    model_config = ConfigDict(extra="ignore")


class PortfolioROISummaryResponse(BaseModel):
    """Aggregated portfolio-level decision ROI analytics."""
    total_decisions: int = Field(..., description="Total decisions considered in scope")
    decisions_with_outcomes: int = Field(..., description="Decisions with recorded outcomes")
    decisions_pending_outcomes: int = Field(..., description="Decisions awaiting outcome recording")
    currency: str = Field("USD", description="Currency for aggregate financials")
    total_predicted_cost: Optional[str] = Field(None, description="Sum of predicted costs for comparable decisions")
    total_actual_cost: Optional[str] = Field(None, description="Sum of actual costs for comparable decisions")
    aggregate_cost_variance: Optional[str] = Field(None, description="total_actual_cost - total_predicted_cost")
    aggregate_cost_variance_percentage: Optional[float] = Field(None, description="((total_actual - total_pred) / total_pred) * 100")
    aggregate_money_saved_vs_prediction: Optional[str] = Field(None, description="total_predicted_cost - total_actual_cost")
    aggregate_baseline_savings: Optional[str] = Field(None, description="Sum of (baseline - actual) for decisions with valid baselines")
    success_counts: Dict[str, int] = Field(default_factory=dict, description="Count of decisions by success classification")
    aggregate_roi: ROIMetrics = Field(..., description="Portfolio aggregate ROI calculation")
    excluded_incomplete_records_count: int = Field(0, description="Records excluded from financial aggregation due to missing data")
    calculation_version: str = Field("1.0", description="ROI engine version")

    model_config = ConfigDict(extra="ignore")


class DashboardSummaryKPIs(BaseModel):
    """High-level summary KPIs for Decision ROI Dashboard."""
    total_decisions: int = Field(..., description="Total decisions matching active filters")
    completed_decisions: int = Field(..., description="Decisions with recorded outcomes")
    pending_decisions: int = Field(..., description="Decisions awaiting outcome recording")
    successful_decisions: int = Field(0, description="Decisions classified as SUCCESS")
    partially_successful_decisions: int = Field(0, description="Decisions classified as PARTIAL_SUCCESS")
    failed_decisions: int = Field(0, description="Decisions classified as FAILURE")
    eligible_completed_decisions: int = Field(0, description="Denominator for rates (successful + partial + failed)")
    success_rate: Optional[float] = Field(None, description="Percentage of eligible decisions that succeeded")
    partial_success_rate: Optional[float] = Field(None, description="Percentage of eligible decisions partially successful")
    failure_rate: Optional[float] = Field(None, description="Percentage of eligible decisions that failed")
    average_cost_difference: Optional[str] = Field(None, description="Mean of (actual_cost - predicted_cost)")
    average_cost_variance_percentage: Optional[float] = Field(None, description="Mean percentage cost variance")
    total_predicted_cost: Optional[str] = Field(None, description="Sum of predicted costs in target currency")
    total_actual_cost: Optional[str] = Field(None, description="Sum of actual costs in target currency")
    forecast_variance: Optional[str] = Field(None, description="predicted_cost - actual_cost (forecast variance)")
    verified_baseline_savings: Optional[str] = Field(None, description="Sum of verified savings vs baseline")
    aggregate_roi: ROIMetrics = Field(..., description="Weighted aggregate portfolio ROI")
    currency: str = Field("USD", description="Currency code for summary values")

    model_config = ConfigDict(extra="ignore")


class PredictionAccuracyMetrics(BaseModel):
    """Prediction error and accuracy metrics for cost and delay."""
    cost_mae: Optional[float] = Field(None, description="Mean Absolute Error for cost predictions")
    cost_mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error for cost predictions")
    cost_rmse: Optional[float] = Field(None, description="Root Mean Squared Error for cost predictions")
    cost_mean_signed_error: Optional[float] = Field(None, description="Mean Signed Error (actual - predicted) for cost")
    cost_records_evaluated: int = Field(0, description="Count of decisions evaluated for cost accuracy")
    delay_mae_days: Optional[float] = Field(None, description="Mean Absolute Error for delay in days")
    delay_mean_error_days: Optional[float] = Field(None, description="Mean Signed Error (actual - predicted) for delay in days")
    delay_records_evaluated: int = Field(0, description="Count of decisions evaluated for delay accuracy")

    model_config = ConfigDict(extra="ignore")


class SuccessBreakdownItem(BaseModel):
    """Single category breakdown for Success vs Failure chart."""
    status: str = Field(..., description="Classification key (SUCCESS, PARTIAL_SUCCESS, FAILURE, PENDING_REVIEW)")
    label: str = Field(..., description="Human-readable category label")
    count: int = Field(..., description="Number of decisions in category")
    percentage_of_eligible: Optional[float] = Field(None, description="Percentage of eligible completed decisions")
    percentage_of_total: float = Field(..., description="Percentage of total decisions in filter scope")
    color: str = Field(..., description="Hex color for consistent visualization")
    description: str = Field(..., description="Criteria defining this category")

    model_config = ConfigDict(extra="ignore")


class CostDifferenceByStrategyItem(BaseModel):
    """Strategy-level cost difference summary."""
    strategy: str = Field(..., description="Operational strategy name")
    count: int = Field(..., description="Decisions with comparable costs")
    average_cost_difference: Optional[str] = Field(None, description="Average actual - predicted cost")
    total_predicted_cost: Optional[str] = Field(None, description="Total predicted cost for strategy")
    total_actual_cost: Optional[str] = Field(None, description="Total actual cost for strategy")

    model_config = ConfigDict(extra="ignore")


class ROIByStrategyItem(BaseModel):
    """Strategy-level ROI and baseline savings comparison."""
    strategy: str = Field(..., description="Operational strategy name")
    total_decisions: int = Field(..., description="Total decisions for this strategy")
    completed_decisions: int = Field(..., description="Completed decisions with outcomes")
    successful_decisions: int = Field(..., description="Decisions classified as SUCCESS")
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    average_cost_difference: Optional[str] = Field(None, description="Average cost difference")
    verified_baseline_savings: Optional[str] = Field(None, description="Total verified baseline savings")
    total_investment_cost: Optional[str] = Field(None, description="Total incremental investment cost")
    total_net_benefit: Optional[str] = Field(None, description="Total net benefit (baseline - actual - addl)")
    roi_percentage: Optional[float] = Field(None, description="Weighted ROI percentage")
    roi_status: str = Field(..., description="CALCULATED or UNAVAILABLE")
    roi_reason: str = Field(..., description="Explanation of ROI calculation or unavailability")

    model_config = ConfigDict(extra="ignore")


class SavingsTimelineItem(BaseModel):
    """Time-series point for savings analysis chart."""
    date: str = Field(..., description="Date formatted as YYYY-MM-DD or period label")
    forecast_variance: float = Field(..., description="Net forecast variance (predicted - actual) in period")
    cumulative_forecast_variance: float = Field(..., description="Cumulative forecast variance to date")
    verified_baseline_savings: float = Field(..., description="Net verified baseline savings in period")
    cumulative_baseline_savings: float = Field(..., description="Cumulative verified baseline savings to date")
    decision_count: int = Field(..., description="Number of decisions recorded on this date")

    model_config = ConfigDict(extra="ignore")


class DecisionPerformanceItem(BaseModel):
    """Detailed decision record for the performance table."""
    decision_id: str = Field(..., description="Decision business identifier")
    db_id: int = Field(..., description="Primary key id")
    shipment_id: Optional[str] = Field(None, description="Target shipment identifier")
    strategy: Optional[str] = Field(None, description="Strategy name")
    decision_name: Optional[str] = Field(None, description="Decision text or option label")
    decision_time: Optional[str] = Field(None, description="ISO timestamp of decision")
    status: str = Field(..., description="Decision operational status (e.g. RECORDED, Pending)")
    evaluation_status: str = Field(..., description="Success evaluation (SUCCESS, FAILURE, etc.)")
    currency: str = Field("USD", description="Currency code")
    predicted_cost: Optional[str] = Field(None, description="Predicted cost formatted")
    actual_cost: Optional[str] = Field(None, description="Actual cost formatted")
    cost_difference: Optional[str] = Field(None, description="actual_cost - predicted_cost")
    cost_variance_pct: Optional[float] = Field(None, description="Percentage cost variance")
    predicted_delay: Optional[float] = Field(None, description="Predicted delay in days")
    actual_delay: Optional[float] = Field(None, description="Actual delay in days")
    delay_difference: Optional[float] = Field(None, description="actual_delay - predicted_delay")
    baseline_savings: Optional[str] = Field(None, description="baseline_cost - actual_cost")
    roi_percentage: Optional[float] = Field(None, description="Decision ROI percentage")
    roi_status: str = Field(..., description="CALCULATED or UNAVAILABLE")

    model_config = ConfigDict(extra="ignore")


class DecisionPerformancePage(BaseModel):
    """Paginated collection of decision performance records."""
    items: List[DecisionPerformanceItem] = Field(default_factory=list)
    total: int = Field(..., description="Total matching items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Page size limit")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = ConfigDict(extra="ignore")


class DataQualityMetrics(BaseModel):
    """Audit and data completeness metrics for the dashboard."""
    total_in_filter: int = Field(..., description="Total decisions matching query filters")
    completed_with_valid_costs: int = Field(..., description="Decisions with valid comparable costs")
    completed_with_valid_delays: int = Field(..., description="Decisions with valid comparable delays")
    decisions_with_valid_baseline: int = Field(..., description="Decisions with valid baseline comparisons")
    excluded_currency_mismatches: int = Field(0, description="Records excluded due to currency mismatch")
    excluded_missing_data: int = Field(0, description="Records excluded due to missing outcome actuals")
    calculation_version: str = Field("1.0", description="Methodology version")
    methodology_notes: List[str] = Field(default_factory=list, description="Methodological disclosures and explanations")

    model_config = ConfigDict(extra="ignore")


class DecisionROIDashboardResponse(PortfolioROISummaryResponse):
    """Comprehensive Decision ROI Dashboard payload (Day 21)."""
    filters: Dict[str, Any] = Field(default_factory=dict, description="Active query filters applied")
    summary: DashboardSummaryKPIs = Field(..., description="High-level dashboard summary cards")
    prediction_accuracy: PredictionAccuracyMetrics = Field(..., description="Cost and delay prediction accuracy metrics")
    success_breakdown: List[SuccessBreakdownItem] = Field(default_factory=list, description="Success vs failure categories")
    cost_difference_by_strategy: List[CostDifferenceByStrategyItem] = Field(default_factory=list, description="Average cost difference grouped by strategy")
    roi_by_strategy: List[ROIByStrategyItem] = Field(default_factory=list, description="ROI and baseline savings by strategy")
    savings_timeline: List[SavingsTimelineItem] = Field(default_factory=list, description="Time series of forecast variance vs baseline savings")
    performance_table: DecisionPerformancePage = Field(..., description="Paginated decision audit table")
    data_quality: DataQualityMetrics = Field(..., description="Data completeness and calculation methodology")

    model_config = ConfigDict(extra="ignore")
